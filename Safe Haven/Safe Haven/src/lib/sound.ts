/**
 * Web Audio API synthesizer helper to play a loud beep alert.
 * Works natively in all browser environments (Edge, Chrome, Safari, etc.)
 * and complies with Expo Web context.
 */
export function playBeepSound() {
  if (typeof window !== 'undefined') {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (AudioContextClass) {
      try {
        const ctx = new AudioContextClass();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        
        osc.connect(gain);
        gain.connect(ctx.destination);
        
        osc.type = 'sine';
        // 880Hz (A5 tone) provides a distinct, clean alert tone
        osc.frequency.setValueAtTime(880, ctx.currentTime);
        
        // Initial volume
        gain.gain.setValueAtTime(0.4, ctx.currentTime);
        
        // Fast fade-out (exponential ramp) to make it a pleasant beep/alert
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.6);
        
        osc.start();
        osc.stop(ctx.currentTime + 0.6);
      } catch (e) {
        console.warn('[Safe Haven] Web Audio beep failed or blocked:', e);
      }
    }
  }
}
