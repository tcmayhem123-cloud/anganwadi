/**
 * Interactive WHO Child Growth Standard Charts using Chart.js.
 * Complies with FR-GM-08: plots child's measurements against official WHO z-score curves (-3, -2, Median, +2, +3 SD)
 * across Weight-for-Age (WFA), Length/Height-for-Age (HAZ), and Weight-for-Height/Length (WHZ).
 */
class GrowthChartRenderer {
  constructor(canvasId) {
    this.canvasId = canvasId;
    this.chart = null;
  }

  render(chartData) {
    const ctx = document.getElementById(this.canvasId);
    if (!ctx) return;

    if (this.chart) {
      this.chart.destroy();
    }

    const curves = chartData.curves;
    const points = chartData.points || [];
    const child = chartData.child;
    const info = chartData.info || {
      indicator: "WFA",
      title: `WHO Growth Standards — ${child.name}`,
      x_label: "Completed Age (Months)",
      y_label: "Measurement"
    };

    const xLabels = curves.labels || curves.months || [];

    // Build dataset for child's actual points
    const childScatterData = points.map(p => ({
      x: p.x !== undefined ? p.x : p.age_months,
      y: p.y !== undefined ? p.y : p.weight_kg,
      whz: p.whz,
      waz: p.waz,
      haz: p.haz,
      date: p.date,
      cls: p.acute_class
    }));

    // Calculate dynamic axis bounds
    const allX = [...xLabels, ...childScatterData.map(d => d.x)].filter(v => v !== undefined && v !== null);
    const minX = Math.min(...allX, 0);
    const maxX = Math.max(...allX, 24);

    const allY = [
      ...curves.sd3pos,
      ...curves.sd3neg,
      ...childScatterData.map(d => d.y)
    ].filter(v => v !== undefined && v !== null && !isNaN(v));

    const minY = Math.floor(Math.min(...allY, 0));
    const maxY = Math.ceil(Math.max(...allY, 15));

    this.chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: xLabels,
        datasets: [
          // Child's actual longitudinal trajectory
          {
            label: `${child.name} (Actual)`,
            data: childScatterData,
            borderColor: '#2563eb', // Royal Blue
            backgroundColor: '#1d4ed8',
            pointBackgroundColor: points.map(p => {
              if (p.acute_class === "SAM") return '#dc2626'; // Red
              if (p.acute_class === "MAM") return '#f59e0b'; // Amber
              return '#16a34a'; // Green
            }),
            pointRadius: 6,
            pointHoverRadius: 8,
            borderWidth: 3,
            fill: false,
            tension: 0.2,
            order: 1
          },
          // +3 SD (Extremely High / Obese)
          {
            label: '+3 SD (Extremely High)',
            data: curves.sd3pos,
            borderColor: '#dc2626',
            borderWidth: 1.5,
            borderDash: [4, 4],
            pointRadius: 0,
            fill: false
          },
          // +2 SD (Overweight)
          {
            label: '+2 SD (Overweight)',
            data: curves.sd2pos,
            borderColor: '#f59e0b',
            borderWidth: 1.5,
            borderDash: [4, 4],
            pointRadius: 0,
            fill: false
          },
          // Median (0 SD)
          {
            label: 'Median / WHO Standard (0 SD)',
            data: curves.median,
            borderColor: '#16a34a', // Emerald Green
            borderWidth: 2.5,
            pointRadius: 0,
            fill: false
          },
          // -2 SD (Moderate Threshold)
          {
            label: '-2 SD (Moderate Threshold)',
            data: curves.sd2neg,
            borderColor: '#f59e0b',
            borderWidth: 1.5,
            borderDash: [4, 4],
            pointRadius: 0,
            fill: false
          },
          // -3 SD (Severe Threshold)
          {
            label: '-3 SD (Severe Malnutrition)',
            data: curves.sd3neg,
            borderColor: '#dc2626', // Red
            borderWidth: 2,
            borderDash: [4, 4],
            pointRadius: 0,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'nearest',
          intersect: false
        },
        plugins: {
          title: {
            display: true,
            text: info.title,
            font: { size: 14, weight: 'bold' }
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                if (context.datasetIndex === 0) {
                  const raw = context.raw;
                  return [
                    `Observed: ${raw.y} (${info.y_label})`,
                    `Dimension: ${raw.x} (${info.x_label})`,
                    `WHZ: ${raw.whz} | WAZ: ${raw.waz} | HAZ: ${raw.haz}`,
                    `Classification: ${raw.cls}`,
                    `Recorded Date: ${raw.date}`
                  ];
                }
                return `${context.dataset.label}: ${context.parsed.y}`;
              }
            }
          },
          legend: {
            position: 'bottom',
            labels: { boxWidth: 12, font: { size: 11 } }
          }
        },
        scales: {
          x: {
            type: 'linear',
            min: minX,
            max: maxX,
            title: {
              display: true,
              text: info.x_label,
              font: { weight: 'bold' }
            }
          },
          y: {
            min: minY,
            max: maxY,
            title: {
              display: true,
              text: info.y_label,
              font: { weight: 'bold' }
            }
          }
        }
      }
    });
  }
}

window.GrowthChartRenderer = GrowthChartRenderer;
