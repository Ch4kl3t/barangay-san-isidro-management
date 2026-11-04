// Minimal Chart.js implementation for offline use - Pie and Bar charts
class SimpleChart {
  constructor(ctx, type, data, options = {}) {
    this.ctx = ctx;
    this.type = type;
    this.data = data;
    this.options = { ...{responsive: true, maintainAspectRatio: true}, ...options };
    this.draw();
  }

  draw() {
    const { width, height } = this.ctx.canvas;
    this.ctx.clearRect(0, 0, width, height);
    
    if (this.type === 'doughnut' || this.type === 'pie') {
      this.drawPie();
    } else if (this.type === 'bar') {
      this.drawBar();
    }
  }

  drawPie() {
    const { width, height } = this.ctx.canvas;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 2 * 0.8;
    
    const data = this.data.datasets[0].data;
    const colors = this.data.datasets[0].backgroundColor;
    const labels = this.data.labels;
    
    let currentAngle = -Math.PI / 2;
    const total = data.reduce((a, b) => a + b, 0);

    data.forEach((value, index) => {
      const sliceAngle = (value / total) * Math.PI * 2;
      
      this.ctx.fillStyle = colors[index];
      this.ctx.beginPath();
      this.ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
      this.ctx.lineTo(centerX, centerY);
      this.ctx.fill();
      
      this.ctx.strokeStyle = '#fff';
      this.ctx.lineWidth = 2;
      this.ctx.stroke();

      currentAngle += sliceAngle;
    });

    // Draw legend
    const legendY = height - 60;
    labels.forEach((label, index) => {
      this.ctx.fillStyle = colors[index];
      this.ctx.fillRect(20, legendY + index * 20, 12, 12);
      this.ctx.fillStyle = '#333';
      this.ctx.font = '12px Inter';
      this.ctx.fillText(`${label}: ${data[index]}`, 40, legendY + index * 20 + 10);
    });
  }

  drawBar() {
    const { width, height } = this.ctx.canvas;
    const data = this.data.datasets[0].data;
    const labels = this.data.labels;
    const colors = this.data.datasets[0].backgroundColor;
    
    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;
    
    const maxValue = Math.max(...data);
    const barWidth = chartWidth / data.length * 0.8;
    const barSpacing = chartWidth / data.length;
    
    // Draw axes
    this.ctx.strokeStyle = '#e2e8f0';
    this.ctx.lineWidth = 1;
    this.ctx.beginPath();
    this.ctx.moveTo(padding, height - padding);
    this.ctx.lineTo(width - padding, height - padding);
    this.ctx.stroke();

    // Draw bars
    data.forEach((value, index) => {
      const barHeight = (value / maxValue) * chartHeight;
      const x = padding + index * barSpacing + (barSpacing - barWidth) / 2;
      const y = height - padding - barHeight;

      this.ctx.fillStyle = colors[index];
      this.ctx.fillRect(x, y, barWidth, barHeight);

      // Labels
      this.ctx.fillStyle = '#333';
      this.ctx.font = '12px Inter';
      this.ctx.textAlign = 'center';
      this.ctx.fillText(labels[index], x + barWidth / 2, height - padding + 20);
      this.ctx.fillText(value, x + barWidth / 2, y - 5);
    });
  }

  update(data) {
    this.data = data;
    this.draw();
  }
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SimpleChart;
}
