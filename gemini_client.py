"""Drop-in replacement for the parts of `ollama.Client` this app uses, powered by
Google's Gemini API free tier (https://aistudio.google.com).

It keeps the same call shape the app already uses, so the rest of the code doesn't change:

    client = Client(api_key=..., timeout=90)
    response = client.chat(model=..., messages=[...], format="json", options={"temperature": 0.3})
    response.message.content                      # the reply text

    for chunk in client.chat(model=..., messages=[...], stream=True):
        chunk.message.content                     # each piece of a streamed reply

Messages use Ollama's format: {"role": "system" | "user" | "assistant", "content": "...",
"images": [<base64 strings>]}.
"""

import base64
import queue
import threading
import time
from types import SimpleNamespace

from google import genai
from google.genai import errors, types


class ResponseError(Exception):
    """Raised when the Gemini API returns an error (same name the app used with Ollama)."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def _wrap(text):
    """Give the reply the same shape as an Ollama response: response.message.content."""
    return SimpleNamespace(message=SimpleNamespace(role="assistant", content=text or ""))


def _mime_type(image_b64):
    """Work out the image type from its first bytes (the apps send PNGs, but be safe)."""
    head = base64.b64decode(image_b64[:32] + "=" * (-len(image_b64[:32]) % 4))
    if head.startswith(b"\x89PNG"):
        return "image/png"
    if head.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"GIF8"):
        return "image/gif"
    return "image/png"


def _convert(messages):
    """Ollama-style messages → (system instruction, Gemini contents)."""
    system_parts = []
    contents = []
    for message in messages:
        role = message.get("role")
        text = str(message.get("content") or "")
        if role == "system":
            if text.strip():
                system_parts.append(text)
            continue

        parts = []
        if text.strip():
            parts.append(types.Part(text=text))
        for image in message.get("images") or []:
            if isinstance(image, (bytes, bytearray)):
                image = base64.b64encode(image).decode("utf-8")
            parts.append(types.Part.from_bytes(data=base64.b64decode(image), mime_type=_mime_type(image)))
        if not parts:
            continue  # Gemini rejects empty messages (e.g. a blank assistant reply)

        contents.append(types.Content(role="model" if role == "assistant" else "user", parts=parts))

    if not contents:
        contents.append(types.Content(role="user", parts=[types.Part(text="Hello")]))
    return "\n\n".join(system_parts) or None, contents



# If the chosen model is busy (503), out of free quota (429), or too slow, try these next.
# Free limits are counted per model, so a different model usually still has room.
FALLBACK_MODELS = ("gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.8-flash")

# Gemini thinks silently before it answers, which is what made simple replies take 15-30 s.
# "minimal" keeps that as short as possible. If a model won't accept it, the same model is
# asked again without the setting.
THINKING_LEVEL = "minimal"

# After a model fails, skip it for a while so later requests don't wait on it again. These
# timers are shared by everyone using the app and by both clients app.py makes.
REST_SECONDS_OUT_OF_QUOTA = 300   # 429: free limit used up, check again in 5 minutes
REST_SECONDS_OTHER = 30           # busy, timed out, or another error
REST_SECONDS_SLOW = 120           # went quiet (no words in time): likely stuck, skip it longer

# Chat replies: nobody waits longer than this for the first words. (Healthy models start
# writing in under 3 s; a stuck one can sit silent for close to a minute.)
TOTAL_WAIT_SECONDS = 10
# If the model being asked is still silent after this long, the next model is started alongside
# it and whichever starts writing first answers. A model that fails outright (e.g. out of free
# quota) hands over to the next one immediately.
HEDGE_SECONDS = 3.5

_resting = {}  # model name -> time.time() until which it is skipped


class ReplyCutOff(Exception):
    """A streamed reply stopped partway through. The part already shown is kept."""


class _TryNext(Exception):
    """One model couldn't answer (busy, out of quota, timed out); move on to the next."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def _models_to_try(model):
    """The chosen model first, then the fallbacks, skipping any that failed a moment ago
    (unless every model is resting; then try them all)."""
    names = [model] + [m for m in FALLBACK_MODELS if m != model]
    now = time.time()
    awake = [name for name in names if _resting.get(name, 0) <= now]
    return awake or names


def _rest(name, reason):
    code = reason.status_code
    seconds = (REST_SECONDS_OUT_OF_QUOTA if code == 429
               else REST_SECONDS_SLOW if code == "slow" else REST_SECONDS_OTHER)
    _resting[name] = time.time() + seconds
    print(f"Gemini {name} unavailable ({code or reason}); skipping it for {seconds}s")


def _awake(name):
    _resting.pop(name, None)


def _rejected_thinking(error):
    """True when a model said no to the thinking setting (then we ask again without it)."""
    return getattr(error, "code", None) == 400 and "think" in str(error).lower()


def _config(system, format, temperature, think):
    return types.GenerateContentConfig(
        system_instruction=system,
        temperature=temperature,
        response_mime_type="application/json" if format == "json" else None,
        thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVEL) if think else None,
    )


def _as_try_next(name, error):
    """Any failure (busy, out of quota, timed out, dropped connection, bad reply) moves on to
    the next model. The reason is printed to the app's logs."""
    if isinstance(error, _TryNext):
        return error
    return _TryNext(f"{name}: {type(error).__name__}: {error}", getattr(error, "code", None))


def _friendly_error(last):
    code = getattr(last, "status_code", None)
    if code == 429:
        return ResponseError(
            "The free AI limit has been reached for now. Please try again in a few minutes.", 429
        )
    if code in (401, 403) or (code == 400 and "api key" in str(last).lower()):
        return ResponseError("The Gemini API key is missing or invalid. Check GEMINI_API_KEY in your secrets.", code)
    return ResponseError("The AI is very busy right now. Please try again in a moment.", code)


class Client:
    def __init__(self, api_key, timeout=None):
        self._timeout = timeout or 90
        http_options = types.HttpOptions(timeout=int(self._timeout * 1000))
        self._client = genai.Client(api_key=api_key, http_options=http_options)

    def chat(self, model, messages, format=None, options=None, stream=False, think=None, **_ignored):
        # `think` was an Ollama setting. Gemini decides how much to think on its own, so it's ignored.
        system, contents = _convert(messages)
        settings = (system, format, (options or {}).get("temperature"))
        names = _models_to_try(model)
        if stream:
            return self._stream(names, contents, settings)

        started = time.time()
        last = None
        for name in names:
            try:
                text = self._ask(name, contents, settings)
                _awake(name)
                print(f"AI timing: answered by {name}, total {time.time() - started:.1f}s")
                return _wrap(text)
            except Exception as error:
                last = _as_try_next(name, error)
                _rest(name, last)
        print(f"AI timing: no model answered after {time.time() - started:.1f}s")
        raise _friendly_error(last)

    # ---------- one attempt ----------

    def _ask(self, name, contents, settings):
        try:
            response = self._client.models.generate_content(
                model=name, contents=contents, config=_config(*settings, think=True))
        except errors.APIError as error:
            if not _rejected_thinking(error):
                raise
            response = self._client.models.generate_content(
                model=name, contents=contents, config=_config(*settings, think=False))
        return response.text

    def _ask_stream(self, name, contents, settings):
        think = True
        while True:
            started = False
            try:
                for chunk in self._client.models.generate_content_stream(
                    model=name, contents=contents, config=_config(*settings, think=think)
                ):
                    started = True
                    yield chunk.text
                return
            except errors.APIError as error:
                if started or not think or not _rejected_thinking(error):
                    raise
                think = False  # this model won't take the thinking setting; ask again without it

    # ---------- streaming with a backup started alongside a silent model ----------

    def _stream(self, names, contents, settings):
        """Stream a reply, starting the next model alongside a silent one so the first words
        arrive within TOTAL_WAIT_SECONDS. Raises ResponseError if nothing answered in time and
        ReplyCutOff if a reply stopped partway through."""
        began = time.time()
        events = queue.Queue()      # (attempt number, kind, value) from the helper threads
        stops = {}                  # attempt number -> Event that tells its thread to stop
        active = set()
        deadline = began + TOTAL_WAIT_SECONDS
        state = {"next": 0, "last_launch": 0.0}
        winner = None
        last = None

        def launch_next():
            i = state["next"]
            if i >= len(names):
                return False
            state["next"] += 1
            state["last_launch"] = time.time()
            stop = threading.Event()
            stops[i] = stop
            active.add(i)

            def run():
                try:
                    for piece in self._ask_stream(names[i], contents, settings):
                        if stop.is_set():
                            return
                        events.put((i, "piece", piece))
                    events.put((i, "end", None))
                except BaseException as error:  # handed to the loop below
                    events.put((i, "error", error))

            threading.Thread(target=run, daemon=True).start()
            return True

        def give_up_on(i, reason):
            active.discard(i)
            stops[i].set()
            _rest(names[i], reason)

        try:
            launch_next()
            # 1) Wait for the first words from any model.
            while winner is None:
                now = time.time()
                if now >= deadline:
                    break
                more_left = state["next"] < len(names)
                next_hedge = state["last_launch"] + HEDGE_SECONDS if more_left else deadline
                try:
                    i, kind, value = events.get(timeout=max(0.01, min(deadline, next_hedge) - now))
                except queue.Empty:
                    if time.time() < deadline and more_left and time.time() >= next_hedge:
                        launch_next()  # still silent: start the next model alongside it
                    continue
                if i not in active:
                    continue  # a model we already gave up on
                if kind == "piece":
                    if value:
                        winner = i
                        _awake(names[i])
                        print(f"AI timing: {names[i]} started writing after {time.time() - began:.1f}s")
                        yield _wrap(value)
                    continue
                reason = (_as_try_next(names[i], value) if kind == "error"
                          else _TryNext("finished without saying anything"))
                give_up_on(i, reason)
                last = reason
                if not launch_next() and not active:
                    break  # every model failed

            if winner is None:
                for i in list(active):  # still silent at the deadline
                    last = _TryNext(f"no words within {TOTAL_WAIT_SECONDS}s", "slow")
                    give_up_on(i, last)
                print(f"AI timing: no model answered after {time.time() - began:.1f}s")
                raise _friendly_error(last)

            # 2) Stop the slower models; they're skipped for a while since they were stuck.
            for i in list(active):
                if i != winner:
                    give_up_on(i, _TryNext("slower than another model", "slow"))

            # 3) Pass along the rest of the winning reply.
            while True:
                try:
                    i, kind, value = events.get(timeout=self._timeout)
                except queue.Empty:
                    raise ReplyCutOff("the reply stopped coming in")
                if i != winner:
                    continue
                if kind == "piece":
                    if value:
                        yield _wrap(value)
                elif kind == "end":
                    print(f"AI timing: {names[winner]} finished after {time.time() - began:.1f}s")
                    return
                else:
                    print(f"AI reply cut off: {type(value).__name__}: {value}")
                    raise ReplyCutOff(str(value))
        finally:
            for stop in stops.values():
                stop.set()
