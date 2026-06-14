# Synthesizer

## Requirements
- **Python Interpreter**: Ensure you have Python installed.
- **Mido**
- **python-rtmidi**
- **numpy**
- **sounddevice**

**You can install them using:**
```console
pip3 install -r requirements.txt
```

## Usage
**Make sure you have a keyboard connected to your computer. Once you have it connected, run the program**
```console
python3 main.py
```

## Creating a custom synthesizer
**Follow this format:**
```json
  {
    "SETTINGS": {
        "MAX_VOICES": [MAX_VOICES],
        "MASTER_VOLUME": [MASTER_VOLUME],
        "ATTACK": [ATTACK],
        "DECAY": [DECAY],
        "SUSTAIN": [SUSTAIN],      
        "RELEASE": [RELEASE]
    },

    "OSCILLATOR": {
        "WAVE_TYPE": [SINE, SAW, SQUARE, TRIANGLE, COSEC]
    },

    "HARMONICS": {
        [HARMOINC]: [VOLUME],
    }
}
```

**I recommend 8 for MAX_VOICES and a maximum of 7 harmonics for the best results**r
