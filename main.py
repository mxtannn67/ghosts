import os, time, random, yaml, glob, subprocess, sys, datetime, pathlib
import pyautogui as pag
import cv2
import numpy as np
from mss import mss

_LAST = {"op": None, "payload": None, "ts": 0.0}
HOME = str(pathlib.Path.home())


def _rand_slug(n=6):
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(random.choice(alphabet) for _ in range(n))

def make_context():
    return {
        "ts": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),  # e.g., 20251007_195501
        "rand": _rand_slug(6)                                     # e.g., k3p9az
    }

def expand(val, ctx):
    if isinstance(val, str):
        out = val
        for k, v in ctx.items():
            out = out.replace("{" + k + "}", str(v))
        return out
    return val


# --------------------------- Logging & Time Helpers ---------------------------

def log_setup(path: str):
    path = os.path.expanduser(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return open(path, "a", buffering=1)

def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def between_active_hours(cfg) -> bool:
    start = cfg["active_hours"]["start"]
    end   = cfg["active_hours"]["end"]
    now   = datetime.datetime.now().time()
    s = datetime.datetime.strptime(start, "%H:%M").time()
    e = datetime.datetime.strptime(end, "%H:%M").time()
    if s <= e:
        return s <= now <= e
    else:
        # handles ranges crossing midnight
        return now >= s or now <= e

# --------------------------- Delay / Humanization -----------------------------

def sleep_range(spec):
    if isinstance(spec, (int, float)):
        time.sleep(float(spec)); return
    if isinstance(spec, str) and "-" in spec:
        a, b = spec.split("-", 1)
        time.sleep(random.uniform(float(a), float(b))); return
    time.sleep(1.0)

def human_type(text, cfg):
    lo = cfg["human_delay"]["key_min_ms"] / 1000
    hi = cfg["human_delay"]["key_max_ms"] / 1000
    for ch in text:
        pag.typewrite(ch)
        time.sleep(random.uniform(lo, hi))

def key_press(key, cfg):
    pag.press(key)
    time.sleep(cfg["human_delay"]["click_ms"] / 1000)

def key_combo(keys, cfg):
    pag.hotkey(*keys)
    time.sleep(cfg["human_delay"]["click_ms"] / 1000)

# --------------------------- YAML & Step Resolution ---------------------------

def load_yaml(p):
    with open(p, "r") as f:
        return yaml.safe_load(f)

def resolve_module_step(step, modules_root):
    if "use" not in step:
        return [step]
    mod, name = step["use"].split(".", 1)
    ypath = os.path.join(modules_root, mod, f"{mod}.yaml")
    y = load_yaml(ypath)
    return y[name].get("steps", [])

# --------------------------- Screen & Image Detection -------------------------

def screen_cap():
    with mss() as sct:
        img = np.array(sct.grab(sct.monitors[0]))
        return img[:, :, :3]  # remove alpha channel

def _match_once(template_path: str, threshold: float):
    scr = screen_cap()
    tpl = cv2.imread(template_path)
    if tpl is None:
        return None
    res = cv2.matchTemplate(scr, tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    if max_val >= threshold:
        h, w = tpl.shape[:2]
        x = max_loc[0] + w // 2
        y = max_loc[1] + h // 2
        return (x, y, w, h)
    return None

def find_click_image(img_path: str, cfg) -> bool:
    deadline = time.time() + cfg["screen"]["search_timeout_sec"]
    threshold = float(cfg["screen"]["confidence"])
    j = cfg["screen"]["move_jitter_px"]

    while time.time() < deadline:
        hit = _match_once(img_path, threshold)
        if hit:
            x, y, w, h = hit
            pag.moveTo(
                x + random.randint(-j, j),
                y + random.randint(-j, j),
                duration=random.uniform(0.2, 0.6)
            )
            pag.click()
            time.sleep(cfg["human_delay"]["click_ms"] / 1000)
            return True
        time.sleep(0.3)
    return False

def _xdotool_focus_by_class(cls: str) -> bool:
    out = subprocess.check_output(
        ["bash", "-lc", f"xdotool search --class '{cls}' || true"],
        text=True, stderr=subprocess.DEVNULL
    )
    ids = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if not ids: return False
    wid = ids[-1]
    subprocess.call(
        ["bash", "-lc", f"xdotool windowactivate --sync {wid}; xdotool windowraise {wid}"],
        stderr=subprocess.DEVNULL
    )
    return True

def _xdotool_focus_by_name(token: str) -> bool:
    out = subprocess.check_output(
        ["bash", "-lc", f"xdotool search --name '{token}' || true"],
        text=True, stderr=subprocess.DEVNULL
    )
    ids = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if not ids: return False
    wid = ids[-1]
    subprocess.call(
        ["bash", "-lc", f"xdotool windowactivate --sync {wid}; xdotool windowraise {wid}"],
        stderr=subprocess.DEVNULL
    )
    return True

def focus_by_class_or_title(token: str, timeout_sec: int = 20) -> bool:
    deadline = time.time() + timeout_sec
    tok_l = token.lower()
    while time.time() < deadline:
        try:
            if _xdotool_focus_by_class(token): return True
        except Exception:
            pass
        try:
            out = subprocess.check_output(["bash", "-lc", "wmctrl -lx"],
                                          text=True, stderr=subprocess.DEVNULL)
            for ln in out.splitlines():
                if tok_l in ln.lower():
                    wid = ln.split(None, 1)[0]
                    subprocess.call(["bash", "-lc", f"wmctrl -ia {wid}"],
                                    stderr=subprocess.DEVNULL)
                    return True
        except Exception:
            pass
        try:
            out = subprocess.check_output(["bash", "-lc", "wmctrl -l"],
                                          text=True, stderr=subprocess.DEVNULL)
            for ln in out.splitlines():
                parts = ln.split(None, 3)
                if len(parts) == 4 and tok_l in parts[3].lower():
                    wid = parts[0]
                    subprocess.call(["bash", "-lc", f"wmctrl -ia {wid}"],
                                    stderr=subprocess.DEVNULL)
                    return True
        except Exception:
            pass
        try:
            if _xdotool_focus_by_name(token): return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

# --------------------------- Core Step Execution ------------------------------

def run_step(step, cfg, logf, cwd, ctx):
    """Execute one step with human-like delays and safety guards."""

    CONTROL_TOKENS = {
        "open_extra",
        "save_page",
        "open_bookmark",
        "add_bookmark",
        "add_bookmark_if_needed",
    }

    # helper: detect url
    def _is_url(s: str) -> bool:
        return isinstance(s, str) and s.startswith(("http://", "https://"))

    # helper: detect repeated typing
    def _duplicate_type(new_text: str, window_sec: float = 2.0) -> bool:
        if not isinstance(new_text, str):
            return False
        if _LAST["op"] != "type":
            return False
        if _LAST.get("payload") != new_text:
            return False
        return (time.time() - _LAST["ts"]) < window_sec

    # helper: detect second URL before Enter
    def _recent_url_conflict(new_text: str, window_sec: float = 5.0) -> bool:
        if not _is_url(new_text):
            return False
        if _LAST["op"] != "type":
            return False
        prev = _LAST.get("payload", "")
        if not _is_url(prev):
            return False
        # skip 2nd URL if typed too soon
        return (time.time() - _LAST["ts"]) < window_sec

    # ------------------- wait -------------------
    if "wait" in step:
        sleep_range(step["wait"])
        return

    # ------------------- type -------------------
    if "type" in step:
        payload = expand(step["type"], ctx)

        if payload in CONTROL_TOKENS:
            logf.write(f"{now_str()} FLAG {payload}\n")
            return
        if _duplicate_type(payload) or _recent_url_conflict(payload):
            return

        logf.write(f"{now_str()} TYPE {payload}\n")
        human_type(payload, cfg)
        _LAST.update({"op": "type", "payload": payload, "ts": time.time()})
        return

    # ---------------- type_oneof ----------------
    if "type_oneof" in step:
        choice_raw = random.choice(step["type_oneof"])
        choice = expand(choice_raw, ctx)

        if isinstance(choice, str) and choice in CONTROL_TOKENS:
            logf.write(f"{now_str()} FLAG {choice}\n")
            return
        if _duplicate_type(choice) or _recent_url_conflict(choice):
            return

        logf.write(f"{now_str()} TYPE {choice}\n")
        human_type(choice, cfg)
        _LAST.update({"op": "type", "payload": choice, "ts": time.time()})
        return

    # ------------------- key -------------------
    if "key" in step:
        payload = f"key:{step['key']}"
        nowt = time.time()
        if _LAST["op"] == "key" and _LAST["payload"] == payload and (nowt - _LAST["ts"]) < 0.8:
            return
        logf.write(f"{now_str()} KEY {step['key']}\n")
        key_press(step["key"], cfg)
        _LAST.update({"op": "key", "payload": payload, "ts": time.time()})
        return

    # ---------------- key_oneof ----------------
    if "key_oneof" in step:
        k = random.choice(step["key_oneof"])
        if k:
            payload = f"key:{k}"
            nowt = time.time()
            if _LAST["op"] == "key" and _LAST["payload"] == payload and (nowt - _LAST["ts"]) < 0.8:
                return
            logf.write(f"{now_str()} KEY {k}\n")
            key_press(k, cfg)
            _LAST.update({"op": "key", "payload": payload, "ts": time.time()})
        return

    # ---------------- keycombo ----------------
    if "keycombo" in step:
        combo = step["keycombo"]
        payload = f"keycombo:{'+'.join(combo)}"
        nowt = time.time()
        if _LAST["op"] == "keycombo" and _LAST["payload"] == payload and (nowt - _LAST["ts"]) < 0.8:
            return
        logf.write(f"{now_str()} HOTKEY {combo}\n")
        key_combo(combo, cfg)
        _LAST.update({"op": "keycombo", "payload": payload, "ts": time.time()})
        return

    # ---------------- click_image -------------
    if "click_image" in step:
        img = step["click_image"]
        candidates = [os.path.join(cwd, "images", img)]
        base = os.path.dirname(os.path.abspath(__file__))
        for mod in ["firefox", "thunderbird", "onlyoffice"]:
            candidates.append(os.path.join(base, "modules", mod, "images", img))
        hit_path = next((p for p in candidates if os.path.exists(p)), None)
        if not hit_path:
            logf.write(f"{now_str()} CLICK_IMAGE {img} MISSING\n")
            time.sleep(1)
            return
        ok = find_click_image(hit_path, cfg)
        logf.write(f"{now_str()} CLICK_IMAGE {hit_path} {'OK' if ok else 'MISS'}\n")
        return

    # ---------------- exec -------------------
    if "exec" in step:
        cmd = expand(step["exec"], ctx)
        logf.write(f"{now_str()} EXEC {cmd}\n")
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
        return

    # ------- focus_window_class -------------
    if "focus_window_class" in step:
        cls = step["focus_window_class"]
        timeout = int(step.get("timeout", 20))
        ok = focus_by_class_or_title(cls, timeout)
        logf.write(f"{now_str()} FOCUS {cls} {'OK' if ok else 'MISS'}\n")
        time.sleep(0.3)
        return

    # ---------------- scroll ----------------
    if "scroll" in step:
        pag.scroll(int(step["scroll"]))
        time.sleep(0.2)
        return

    # ---------------- wiggle ----------------
    if "wiggle" in step:
        dx, dy, dur = step["wiggle"].split(",")
        x, y = pag.position()
        pag.moveTo(x + int(dx), y + int(dy), duration=float(dur))
        pag.moveTo(x, y, duration=float(dur))
        return

    # ------------- unknown -----------------
    logf.write(f"{now_str()} UNKNOWN_STEP {step}\n")



# --------------------------- Action Runner ------------------------------------

def run_action(action_path, cfg, logf, modules_root):
    action = load_yaml(action_path)
    ctx = make_context()

    logf.write(f"\n{now_str()} START_ACTION {action.get('name')}\n")
    steps = action.get("steps", [])
    expanded = []

    for st in steps:
        if "use" in st:
            # Expand the referenced module steps
            expanded.extend(resolve_module_step(st, modules_root))
            # If the user put extra keys alongside "use", keep them as a follow-up step
            rest = {k: v for k, v in st.items() if k != "use"}
            if rest:
                expanded.append(rest)
        else:
            # Plain step: add once (do NOT expand/duplicate)
            expanded.append(st)

    for st in expanded:
        run_step(st, cfg, logf, cwd=os.path.dirname(action_path), ctx=ctx)

    logf.write(f"{now_str()} END_ACTION\n")
    

def run_seed_notes(base, cfg, logf, modules_root):
    """Run write_notes.yaml once at startup so there is always at least one doc to edit."""
    seed_path = os.path.join(base, "actions", "write_notes.yaml")
    try:
        logf.write(f"{now_str()} SEED start (write_notes.yaml)\n")
        run_action(seed_path, cfg, logf, modules_root)
        logf.write(f"{now_str()} SEED done\n")
    except Exception as e:
        logf.write(f"{now_str()} SEED ERROR {e}\n")

#------------------------- Main Loop ----------------------------------------

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    cfg = load_yaml(os.path.join(base, "settings.yaml"))
    logf = log_setup(cfg["log_path"])
    modules_root = os.path.join(base, "modules")
    
    # Run write_notes once BEFORE any other actions
    run_seed_notes(base, cfg, logf, modules_root)

    allowed_actions = [
        os.path.join(base, "actions", "browse_many.yaml"),
        os.path.join(base, "actions", "write_notes.yaml"),
        os.path.join(base, "actions", "click_link_email.yaml"),
        os.path.join(base, "actions", "open_attachment_email.yaml"),
        os.path.join(base, "actions", "edit_doc.yaml"),
        os.path.join(base, "actions", "draft_mail.yaml"),
    ]

    logf.write(f"{now_str()} START_LOOP (infinite random actions)\n")

    while True:
        if between_active_hours(cfg):
            chosen = random.choice(allowed_actions)
            try:
                run_action(chosen, cfg, logf, modules_root)
            except Exception as e:
                logf.write(f"{now_str()} ERROR {e}\n")
        else:
            logf.write(f"{now_str()} SKIPPED (outside active hours)\n")

        # small delay between runs (to look human)
        sleep_range("20-60")  # random wait 20–60 seconds before next action 
# --------------------------- Entrypoint ---------------------------------------

if __name__ == "__main__":
    pag.FAILSAFE = True  # move mouse to top-left to abort
    main()

