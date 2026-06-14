import mido
import numpy as np
import sounddevice as sd
import threading
import json

# ---------------------------
# Load Synth Preset
# ---------------------------

with open("Synths/synth1.json", "r", encoding="utf-8") as file:
    SYNTH = json.load(file)

print("Loaded preset:")
print(SYNTH)

settings = SYNTH.get("SETTINGS", {})
oscillator = SYNTH.get("OSCILLATOR", {})
harmonics = SYNTH.get("HARMONICS", {"1": 1.0})

sustain_pedal = False

# ---------------------------
# Settings
# ---------------------------

SAMPLE_RATE = 44100

MASTER_VOLUME = settings.get("MASTER_VOLUME", 0.2)

ATTACK = settings.get("ATTACK", 0.01)
DECAY = settings.get("DECAY", 0.1)
SUSTAIN = settings.get("SUSTAIN", 0.7)
RELEASE = settings.get("RELEASE", 0.2)
MAX_VOICES = settings.get("MAX_VOICES", 8)

WAVE_TYPE = oscillator.get("WAVE_TYPE", "SINE").upper()

# ---------------------------
# Note Storage
# ---------------------------

active_notes = {}
phase = {}

# ---------------------------
# Helpers
# ---------------------------

def midi_to_freq(note):
    return 440 * (2 ** ((note - 69) / 12))

# ---------------------------
# Wave Generator
# ---------------------------

def generate_wave(phase_value, wave_type):
    if wave_type == "SINE":
        return np.sin(phase_value)

    elif wave_type == "SQUARE":
        return np.sign(np.sin(phase_value))

    elif wave_type == "SAW":
        return 2 * ((phase_value / (2 * np.pi)) % 1) - 1
    
    elif wave_type == "COSEC":
        sine = np.sin(phase_value)

        # force sign away from 0
        if sine >= 0:
            sine += 0.05
        else:
            sine -= 0.05

        return 1.0 / sine
    
    elif wave_type == "ABSOLUTESINE":
        return abs(np.sin(phase_value))
    
    elif wave_type == "TRIANGLE":
        return 2 * abs((phase_value % 1) - 0.5) - 1

    return np.sin(phase_value)

# ---------------------------
# Audio Callback
# ---------------------------

def audio_callback(outdata, frames, time, status):
    buffer = np.zeros(frames, dtype=np.float32)

    notes_snapshot = list(active_notes.items())
    notes_to_remove = []

    for note, data in notes_snapshot:

        freq = midi_to_freq(note)

        if note not in phase:
            phase[note] = 0.0

        increment = 2 * np.pi * freq / SAMPLE_RATE

        velocity = data["velocity"]

        for frame in range(frames):

            # -------------------
            # ADSR
            # -------------------

            if data["state"] == "attack":
                data["level"] += 1 / (ATTACK * SAMPLE_RATE)

                if data["level"] >= 1.0:
                    data["level"] = 1.0
                    data["state"] = "decay"

            elif data["state"] == "decay":
                data["level"] -= (1 - SUSTAIN) / (DECAY * SAMPLE_RATE)

                if data["level"] <= SUSTAIN:
                    data["level"] = SUSTAIN
                    data["state"] = "sustain"

            elif data["state"] == "release":
                data["level"] -= 1 / (RELEASE * SAMPLE_RATE)

                if data["level"] <= 0:
                    data["level"] = 0
                    notes_to_remove.append(note)
                    break

            # -------------------
            # Oscillator + Harmonics
            # -------------------

            sample = 0.0

            for harmonic, gain in harmonics.items():

                harmonic = float(harmonic)

                phase_h = harmonic * phase[note]

                wave = generate_wave(
                    phase_h,
                    WAVE_TYPE
                )

                sample += gain * wave

            
            # Apply velocity + ADSR
            sample *= velocity * data["level"]

            buffer[frame] += sample

            phase[note] += increment

            if phase[note] > 2 * np.pi:
                phase[note] -= 2 * np.pi

    # -------------------
    # Cleanup released notes
    # -------------------

    for note in notes_to_remove:
        active_notes.pop(note, None)
        phase.pop(note, None)

    # -------------------
    # Prevent clipping
    # -------------------

    if active_notes:
        buffer /= len(active_notes)

    buffer *= MASTER_VOLUME

    outdata[:] = buffer.reshape(-1, 1)

# ---------------------------
# MIDI Thread
# ---------------------------

def midi_thread():
    global sustain_pedal

    ports = mido.get_input_names()

    if not ports:
        print("No MIDI devices found.")
        return

    print("\nAvailable MIDI Inputs:")
    for i, port in enumerate(ports):
        print(f"{i}: {port}")

    port_name = ports[0]
    print(f"\nUsing: {port_name}")

    with mido.open_input(port_name) as port:

        for msg in port:

            # ---------------------------
            # Sustain pedal (CC 64)
            # ---------------------------
            if msg.type == "control_change" and msg.control == 64:

                if msg.value >= 64:
                    sustain_pedal = True
                else:
                    sustain_pedal = False

                    # Pedal released → release any held notes
                    for note, data in active_notes.items():
                        if not data["key_down"]:
                            data["state"] = "release"

            # ---------------------------
            # Note ON
            # ---------------------------
            if msg.type == "note_on" and msg.velocity > 0:

                # if note already exists, refresh it
                if msg.note in active_notes:
                    del active_notes[msg.note]

                # voice limit check
                if len(active_notes) >= MAX_VOICES:
                    oldest_note = next(iter(active_notes))
                    del active_notes[oldest_note]
                    phase.pop(oldest_note, None)

                active_notes[msg.note] = {
                    "velocity": msg.velocity / 127.0,
                    "state": "attack",
                    "level": 0.0,
                    "key_down": True
                }

            # ---------------------------
            # Note OFF
            # ---------------------------
            elif msg.type == "note_off" or (
                msg.type == "note_on" and msg.velocity == 0
            ):

                if msg.note in active_notes:

                    active_notes[msg.note]["key_down"] = False

                    if sustain_pedal:
                        # keep sounding until pedal lifts
                        pass
                    else:
                        active_notes[msg.note]["state"] = "release"

# ---------------------------
# Start
# ---------------------------

threading.Thread(
    target=midi_thread,
    daemon=True
).start()

with sd.OutputStream(
    samplerate=SAMPLE_RATE,
    channels=1,
    callback=audio_callback
):
    print("\nSynth running...")
    input("Press Enter to quit...\n")