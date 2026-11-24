import React, { useRef, useEffect } from 'react';

export default function AudioVisualizer({ audioData, isCalling, isMuted }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    // Draw subtle grid lines (Swiss aesthetic)
    ctx.strokeStyle = '#2A2A28';
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 4]);

    // Center horizontal datum line
    ctx.beginPath();
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();

    ctx.setLineDash([]); // Reset line dash

    if (!isCalling) {
      // Idle straight line
      ctx.strokeStyle = '#444442';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(0, height / 2);
      ctx.lineTo(width, height / 2);
      ctx.stroke();
      return;
    }

    if (isMuted) {
      // Muted line with small dash
      ctx.strokeStyle = '#6E6E6A';
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(0, height / 2);
      ctx.lineTo(width, height / 2);
      ctx.stroke();
      return;
    }

    // Dynamic reactive waveform bars
    const barsCount = 36;
    const barWidth = 4;
    const gap = (width - barsCount * barWidth) / (barsCount + 1);

    for (let i = 0; i < barsCount; i++) {
      const dataVal = audioData && audioData[i] ? audioData[i] : (Math.sin(Date.now() / 200 + i * 0.4) * 15 + 20);
      const normalizedHeight = Math.max(4, (dataVal / 255) * (height * 0.8));
      const x = gap + i * (barWidth + gap);
      const y = (height - normalizedHeight) / 2;

      // Gradient with burnt-orange accent
      const gradient = ctx.createLinearGradient(0, y, 0, y + normalizedHeight);
      gradient.addColorStop(0, '#FF4F00');
      gradient.addColorStop(1, '#FF7A3D');

      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, normalizedHeight, 2);
      ctx.fill();
    }
  }, [audioData, isCalling, isMuted]);

  return (
    <div className='relative w-full h-16 bg-[#181817] rounded-md overflow-hidden border border-[#2A2A28] flex items-center justify-center p-1 shadow-inner'>
      <canvas
        ref={canvasRef}
        width={380}
        height={60}
        className='w-full h-full'
      />
      <div className='absolute bottom-1 right-2 flex items-center gap-1 font-mono text-[9px] text-[#888884] uppercase tracking-wider'>
        <span className='inline-block w-1.5 h-1.5 rounded-full bg-burnt-orange animate-pulse'></span>
        <span>PCM // 16k</span>
      </div>
    </div>
  );
}