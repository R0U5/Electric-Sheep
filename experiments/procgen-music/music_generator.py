#!/usr/bin/env python3
"""
Procedural Music Generator — Goblin's Daily Build
Synthesizes drum patterns + melody and writes a WAV file.
No external dependencies beyond numpy and stdlib wave.
"""

import numpy as np
import wave
import struct
import os
import math

SAMPLE_RATE = 44100
BPM = 120
BEAT_DURATION = 60.0 / BPM
BAR_DURATION = BEAT_DURATION * 4
BARS = 4
TOTAL_SAMPLES = int(SAMPLE_RATE * BAR_DURATION * BARS)

def write_wav(filepath, audio, normalize=True):
    """Write stereo WAV file."""
    if normalize:
        audio = audio / np.max(np.abs(audio)) * 0.9
    audio = np.clip(audio, -1.0, 1.0)
    with wave.open(filepath, 'w') as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        packed = struct.pack('<hh', 0, 0)  # placeholder
        # Build interleaved stereo samples
        left = (audio[:, 0] * 32767).astype(np.int16)
        right = (audio[:, 1] * 32767).astype(np.int16)
        interleaved = np.empty((len(left) * 2,), dtype=np.int16)
        interleaved[0::2] = left
        interleaved[1::2] = right
        wav.writeframes(interleaved.tobytes())

def sine_wave(freq, duration, phase=0.0):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t + phase)

def noise(duration):
    return np.random.uniform(-1.0, 1.0, int(SAMPLE_RATE * duration))

def envelope(audio, attack=0.001, decay=0.1, sustain=0.0, release=0.05):
    """Apply ADSR-style amplitude envelope."""
    n = len(audio)
    env = np.ones(n)
    a_samples = int(attack * SAMPLE_RATE)
    d_samples = int(decay * SAMPLE_RATE)
    r_samples = int(release * SAMPLE_RATE)
    idx = 0
    # Attack
    if a_samples > 0 and idx < n:
        env[idx:idx+a_samples] = np.linspace(0, 1, a_samples)
        idx += a_samples
    # Decay
    if d_samples > 0 and idx < n:
        end = min(idx + d_samples, n)
        env[idx:end] = np.linspace(1, sustain, end - idx)
        idx = end
    # Sustain / hold
    if idx < n:
        env[idx:] = sustain
    # Release
    if r_samples > 0 and n > r_samples:
        env[-r_samples:] = np.linspace(sustain, 0, r_samples)
    return audio * env

def kick(timestamp, duration=0.3):
    """Kick drum: sine with fast pitch drop + amplitude decay."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    pitch_curve = 150 * np.exp(-t * 30) + 50  # 150Hz -> 50Hz
    phase = 2 * np.pi * np.cumsum(pitch_curve) / SAMPLE_RATE
    wave = np.sin(phase)
    # Add a bit of harmonics
    wave += 0.3 * np.sin(2 * phase)
    env = np.exp(-t * 15)
    return timestamp, wave * env

def snare(timestamp, duration=0.2):
    """Snare: filtered noise burst + body tone."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    # Noise component (snare wires)
    noise_part = np.random.uniform(-1.0, 1.0, n)
    noise_part = noise_part * np.exp(-t * 25)
    # Body tone (200Hz)
    body = 0.6 * np.sin(2 * np.pi * 200 * t) * np.exp(-t * 20)
    combined = noise_part + body
    return timestamp, combined

def hihat(timestamp, duration=0.08, open_hat=False):
    """Hi-hat: high-frequency filtered noise."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    noise_part = np.random.uniform(-1.0, 1.0, n)
    # Simple high-pass模拟 (differentiator + decay)
    filtered = np.diff(np.concatenate([np.array([0]), noise_part]))
    decay_rate = 40 if open_hat else 60
    env = np.exp(-t * decay_rate)
    return timestamp, filtered[:n] * env * 0.4

def bass_note(freq, timestamp, duration, velocity=0.8):
    """Bass note: sine wave with slight saturation."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    wave = np.sin(2 * np.pi * freq * t)
    # Soft clipping for warmth
    wave = np.tanh(wave * 1.5) * 0.7
    env = np.ones(n)
    attack = int(0.01 * SAMPLE_RATE)
    env[:attack] = np.linspace(0, 1, attack)
    release = int(0.05 * SAMPLE_RATE)
    env[-release:] = np.linspace(1, 0, release)
    return timestamp, wave * env * velocity

def lead_note(freq, timestamp, duration, velocity=0.5):
    """Lead synth: sine with gentle vibrato and longer envelope."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    # Vibrato
    vib = 0.003 * np.sin(2 * np.pi * 5 * t)
    phase = 2 * np.pi * freq * t + vib * 2 * np.pi * freq
    wave = np.sin(phase)
    # Add slight detuned double
    wave += 0.3 * np.sin(2 * np.pi * freq * 1.005 * t)
    env = np.ones(n)
    attack = int(0.02 * SAMPLE_RATE)
    env[:attack] = np.linspace(0, 1, attack)
    decay = int(0.1 * SAMPLE_RATE)
    if decay > 0 and attack < n:
        end = min(attack + decay, n)
        env[attack:end] = np.linspace(1, 0.6, end - attack)
    release = int(0.15 * SAMPLE_RATE)
    if release > 0 and n > release:
        env[-release:] = np.linspace(0.6, 0, release)
    return timestamp, wave * env * velocity

def place_audio(audio, audio_data, timestamp):
    """Mix audio_data (mono) into stereo audio buffer at timestamp (in seconds)."""
    start = int(timestamp * SAMPLE_RATE)
    n = len(audio_data)
    end = min(start + n, len(audio))
    if start >= len(audio):
        return
    available = end - start
    chunk = audio_data[:available]
    # Convert mono to stereo by repeating on both channels
    stereo_chunk = np.column_stack([chunk, chunk])
    audio[start:end] += stereo_chunk

# Pentatonic scale frequencies (C minor pentatonic across 2 octaves)
# C Eb F G Bb
SCALE_FREQS = [
    130.81, 155.56, 174.61, 196.00, 233.08,  # C3-Eb3-F3-G3-Bb3
    261.63, 311.13, 349.23, 392.00, 466.16   # C4-Eb4-F4-G4-Bb4
]
BASS_FREQS = [65.41, 77.78, 87.31, 98.00]  # C2-G2

def main():
    np.random.seed(os.urandom(4)[0] % 256 + 1)
    
    audio = np.zeros((TOTAL_SAMPLES, 2))
    
    # --- DRUMS ---
    # 4-bar pattern at 120BPM = 16 beats per bar
    beats_per_bar = 4
    total_beats = BARS * beats_per_bar
    
    # Kick on 1 and 3, with variations
    kick_pattern = [0, 2, 5, 7, 10, 12, 14]  # beat indices
    for beat in kick_pattern:
        ts = beat * BEAT_DURATION / beats_per_bar
        ts_abs = ts
        _, kick_snd = kick(0, 0.35)
        place_audio(audio, kick_snd, ts_abs)
        # Ghost kick on some off-beats
        if beat % 2 == 0 and np.random.rand() > 0.5:
            _, ghost = kick(0, 0.2)
            place_audio(audio, ghost * 0.4, ts_abs + BEAT_DURATION / beats_per_bar * 0.5)
    
    # Snare on 2 and 4, some variations
    snare_pattern = [1, 3, 5, 9, 11, 13, 15]
    for beat in snare_pattern:
        ts = beat * BEAT_DURATION / beats_per_bar
        _, snare_snd = snare(0, 0.2)
        place_audio(audio, snare_snd, ts)
    
    # Hi-hats: 8th notes with some velocity variation
    for bar in range(BARS):
        bar_start = bar * BAR_DURATION
        for step in range(8):
            ts = bar_start + step * (BEAT_DURATION / 2)
            _, hat = hihat(0, 0.06 + np.random.rand() * 0.02)
            velocity = 0.3 + np.random.rand() * 0.4
            if step % 2 == 1:
                velocity *= 0.7  # off-beats softer
            place_audio(audio, hat * velocity, ts)
    
    # --- BASS LINE ---
    # Follows chord roots: C minor for first 2 bars, F minor for last 2
    # Bass notes on each beat
    bass_pattern = [
        (0, BASS_FREQS[0]),        # C2
        (1 * BEAT_DURATION, BASS_FREQS[1]),  # G2
        (2 * BEAT_DURATION, BASS_FREQS[0]),  # C2
        (3 * BEAT_DURATION, BASS_FREQS[2]),  # F2 (flatted 7th of C)
        (BAR_DURATION, BASS_FREQS[3]),  # G2 bar 2
        (BAR_DURATION + BEAT_DURATION, BASS_FREQS[2]),  # F2
        (BAR_DURATION + 2 * BEAT_DURATION, BASS_FREQS[2]),  # F2
        (BAR_DURATION + 3 * BEAT_DURATION, BASS_FREQS[2]),  # F2
        (2 * BAR_DURATION, BASS_FREQS[3]),  # G2 bar 3
        (2 * BAR_DURATION + BEAT_DURATION, BASS_FREQS[3]),  # G2
        (2 * BAR_DURATION + 2 * BEAT_DURATION, BASS_FREQS[3]),  # G2
        (2 * BAR_DURATION + 3 * BEAT_DURATION, BASS_FREQS[0]),  # C2
        (3 * BAR_DURATION, BASS_FREQS[2]),  # F2 bar 4
        (3 * BAR_DURATION + BEAT_DURATION, BASS_FREQS[3]),  # G2
        (3 * BAR_DURATION + 2 * BEAT_DURATION, BASS_FREQS[0]),  # C2
        (3 * BAR_DURATION + 3 * BEAT_DURATION, BASS_FREQS[1]),  # G2
    ]
    
    for ts, freq in bass_pattern:
        _, bass_snd = bass_note(freq, 0, BEAT_DURATION * 0.8, velocity=0.6)
        place_audio(audio, bass_snd, ts)
    
    # --- LEAD MELODY ---
    # Pick random notes from pentatonic scale, place on beat
    melody_notes = []
    for bar in range(BARS):
        bar_start = bar * BAR_DURATION
        # 4 notes per bar, some variation
        for i in range(4):
            note_idx = np.random.randint(0, len(SCALE_FREQS))
            freq = SCALE_FREQS[note_idx]
            ts = bar_start + i * BEAT_DURATION
            # Vary note length
            dur = BEAT_DURATION * (0.7 + np.random.rand() * 0.3)
            _, lead_snd = lead_note(freq, 0, dur, velocity=0.35)
            place_audio(audio, lead_snd, ts)
            melody_notes.append((ts, freq))
    
    # --- SPARKLE: high frequency arpeggios ---
    sparkle_notes = [523.25, 659.25, 783.99, 1046.50]  # C5-E5-G5-C6
    for bar in range(BARS):
        if np.random.rand() > 0.4:
            bar_start = bar * BAR_DURATION
            start_beat = np.random.randint(0, 4)
            ts = bar_start + start_beat * BEAT_DURATION
            for step in range(4):
                freq = sparkle_notes[np.random.randint(0, len(sparkle_notes))]
                _, sparkle = lead_note(freq, 0, 0.1, velocity=0.2)
                place_audio(audio, sparkle, ts + step * (BEAT_DURATION / 4))
    
    # --- MASTER PROCESSING ---
    # Soft clip the final mix
    audio = np.tanh(audio * 1.2)
    
    # Write output
    out_path = os.path.join(os.path.dirname(__file__), 'output.wav')
    write_wav(out_path, audio)
    
    duration = TOTAL_SAMPLES / SAMPLE_RATE
    peak = np.max(np.abs(audio))
    rms = np.sqrt(np.mean(audio**2))
    
    print(f"✓ Generated {BARS}-bar track at {BPM} BPM")
    print(f"  Duration: {duration:.2f}s, Peak: {peak:.3f}, RMS: {rms:.4f}")
    print(f"  Output: {out_path}")
    print(f"  Melody notes placed: {len(melody_notes)}")
    print(f"  Bass pattern entries: {len(bass_pattern)}")

if __name__ == '__main__':
    main()