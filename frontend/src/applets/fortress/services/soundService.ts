
import * as Tone from 'tone';

class SoundService {
  private buildSynth: Tone.Synth;
  private explosionSynth: Tone.MetalSynth;
  private musicLoop: Tone.Loop | null = null;
  private isInitialized = false;

  constructor() {
    this.buildSynth = new Tone.Synth({
      oscillator: { type: 'square' },
      envelope: { attack: 0.01, decay: 0.1, sustain: 0.2, release: 0.1 },
    }).toDestination();
    
    this.explosionSynth = new Tone.MetalSynth({
      frequency: 50,
      envelope: { attack: 0.001, decay: 0.4, release: 0.2 },
      harmonicity: 5.1,
      modulationIndex: 32,
      resonance: 4000,
      octaves: 1.5
    }).toDestination();
    this.explosionSynth.volume.value = -10;
  }

  private async initialize() {
    if (Tone.context.state !== 'running') {
      await Tone.start();
    }
    this.isInitialized = true;
  }

  public async playSound(sound: 'build' | 'explosion' | 'click') {
    if (!this.isInitialized) await this.initialize();
    
    const now = Tone.now();
    switch (sound) {
      case 'build':
        this.buildSynth.triggerAttackRelease('C4', '8n', now);
        break;
      case 'explosion':
        this.explosionSynth.triggerAttackRelease('C2', '4n', now);
        break;
      case 'click':
        // A simple synth for UI clicks
        const clickSynth = new Tone.MembraneSynth().toDestination();
        clickSynth.triggerAttackRelease("C2", "8n", now);
        break;
    }
  }

  public async playMusic() {
    if (!this.isInitialized) await this.initialize();

    if (this.musicLoop) {
      this.musicLoop.start(0);
      return;
    }

    const synth = new Tone.PolySynth(Tone.Synth, {
      oscillator: { type: "triangle8" },
      envelope: { attack: 0.005, decay: 0.1, sustain: 0.3, release: 1 },
    }).toDestination();
    synth.volume.value = -18;
    
    const pattern = new Tone.Pattern((time, note) => {
      synth.triggerAttackRelease(note, "8n", time);
    }, ["C2", "G2", "C3", "E3", "G3", "C4"], "upDown");
    
    pattern.interval = "4n";

    this.musicLoop = new Tone.Loop(time => {
        pattern.start(time).stop(time + 4);
    }, "4m").start(0);

    Tone.Transport.start();
  }

  public stopMusic() {
    if (this.musicLoop) {
      this.musicLoop.stop(0);
    }
    Tone.Transport.stop();
  }
}

export const soundService = new SoundService();
