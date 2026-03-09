const streamBarsContainer = document.getElementById("streamBars");
const leftMatrix = document.getElementById("leftMatrix");
const rightMatrix = document.getElementById("rightMatrix");

function fillMatrix(container, cells = 56) {
  const entries = [];
  for (let i = 0; i < cells; i += 1) {
    const cell = document.createElement("span");
    container.appendChild(cell);
    entries.push(cell);
  }

  setInterval(() => {
    entries.forEach((entry, idx) => {
      const heat = (Math.sin(Date.now() * 0.002 + idx) + 1) * 0.5;
      entry.classList.toggle("hot", heat > 0.82 || Math.random() > 0.94);
      entry.style.opacity = `${0.3 + heat * 0.7}`;
    });
  }, 300);
}

function createBars(container, count, min, max) {
  const bars = [];
  for (let i = 0; i < count; i += 1) {
    const bar = document.createElement("span");
    bar.style.height = `${min}%`;
    container.appendChild(bar);
    bars.push(bar);
  }
  return bars;
}

const bars = createBars(streamBarsContainer, 92, 8, 100);

function animateBars() {
  setInterval(() => {
    bars.forEach((bar, idx) => {
      const wave = Math.sin(Date.now() * 0.0022 + idx * 0.32) * 33;
      const randomBoost = Math.random() * 18;
      const value = Math.max(8, Math.min(100, 18 + wave + randomBoost));
      bar.style.height = `${value}%`;
      bar.style.opacity = `${0.55 + value / 220}`;
    });
  }, 260);
}

function initRings() {
  document.querySelectorAll(".ring").forEach((ring) => {
    const progress = ring.querySelector(".progress");
    const value = Number(ring.dataset.value || 0);
    const radius = Number(progress.getAttribute("r"));
    const circumference = 2 * Math.PI * radius;

    progress.style.strokeDasharray = `${circumference}`;
    progress.style.strokeDashoffset = `${circumference}`;

    requestAnimationFrame(() => {
      progress.style.strokeDashoffset = `${circumference - (value / 100) * circumference}`;
    });
  });
}

const canvas = document.getElementById("globeCanvas");
const ctx = canvas.getContext("2d");

const globe = {
  width: canvas.width,
  height: canvas.height,
  radius: 255,
  centerX: canvas.width / 2,
  centerY: canvas.height / 2,
  rotY: 0,
  tiltX: -0.38
};

const nodes = [
  { name: "Bhagsar", lat: 29.34, lon: 74.17 },
  { name: "Bengaluru", lat: 12.9716, lon: 77.5946 },
  { name: "London", lat: 51.5072, lon: -0.1276 },
  { name: "Singapore", lat: 1.3521, lon: 103.8198 },
  { name: "SanFrancisco", lat: 37.7749, lon: -122.4194 }
];

const links = [
  [0, 1],
  [0, 2],
  [1, 3],
  [3, 4],
  [0, 3]
];

function toRad(deg) {
  return (deg * Math.PI) / 180;
}

function project(lat, lon, rotY) {
  const phi = toRad(90 - lat);
  const theta = toRad(lon) + rotY;

  const x = globe.radius * Math.sin(phi) * Math.cos(theta);
  const y = globe.radius * Math.cos(phi);
  const z = globe.radius * Math.sin(phi) * Math.sin(theta);

  const yTilt = y * Math.cos(globe.tiltX) - z * Math.sin(globe.tiltX);
  const zTilt = y * Math.sin(globe.tiltX) + z * Math.cos(globe.tiltX);

  return {
    x: globe.centerX + x,
    y: globe.centerY + yTilt,
    z: zTilt
  };
}

function drawSphere() {
  const grad = ctx.createRadialGradient(
    globe.centerX - 60,
    globe.centerY - 100,
    35,
    globe.centerX,
    globe.centerY,
    globe.radius + 30
  );

  grad.addColorStop(0, "rgba(255,255,255,0.34)");
  grad.addColorStop(0.32, "rgba(209,218,231,0.22)");
  grad.addColorStop(0.64, "rgba(34,43,55,0.72)");
  grad.addColorStop(1, "rgba(5,7,12,0.98)");

  ctx.beginPath();
  ctx.arc(globe.centerX, globe.centerY, globe.radius, 0, Math.PI * 2);
  ctx.fillStyle = grad;
  ctx.fill();

  ctx.lineWidth = 1.5;
  ctx.strokeStyle = "rgba(255,255,255,0.34)";
  ctx.stroke();

  const redGlow = ctx.createRadialGradient(
    globe.centerX - globe.radius * 0.55,
    globe.centerY - globe.radius * 0.32,
    20,
    globe.centerX - globe.radius * 0.52,
    globe.centerY - globe.radius * 0.3,
    globe.radius * 0.95
  );
  redGlow.addColorStop(0, "rgba(255,34,34,0.26)");
  redGlow.addColorStop(1, "rgba(255,34,34,0)");

  ctx.beginPath();
  ctx.arc(globe.centerX, globe.centerY, globe.radius, 0, Math.PI * 2);
  ctx.fillStyle = redGlow;
  ctx.fill();
}

function drawGrid() {
  ctx.save();
  ctx.beginPath();
  ctx.arc(globe.centerX, globe.centerY, globe.radius, 0, Math.PI * 2);
  ctx.clip();

  ctx.lineWidth = 1;
  ctx.strokeStyle = "rgba(255,255,255,0.24)";

  for (let lat = -75; lat <= 75; lat += 15) {
    ctx.beginPath();
    for (let lon = -180; lon <= 180; lon += 3) {
      const p = project(lat, lon, globe.rotY);
      if (lon === -180) {
        ctx.moveTo(p.x, p.y);
      } else {
        ctx.lineTo(p.x, p.y);
      }
    }
    ctx.stroke();
  }

  for (let lon = -180; lon < 180; lon += 15) {
    ctx.beginPath();
    for (let lat = -90; lat <= 90; lat += 3) {
      const p = project(lat, lon, globe.rotY);
      if (lat === -90) {
        ctx.moveTo(p.x, p.y);
      } else {
        ctx.lineTo(p.x, p.y);
      }
    }
    ctx.stroke();
  }

  ctx.restore();
}

function drawTicks() {
  const count = 140;
  for (let i = 0; i < count; i += 1) {
    const ang = (i / count) * Math.PI * 2 + globe.rotY * 0.28;
    const inner = globe.radius + 10;
    const outer = i % 4 === 0 ? globe.radius + 38 : globe.radius + 24;

    ctx.beginPath();
    ctx.moveTo(globe.centerX + Math.cos(ang) * inner, globe.centerY + Math.sin(ang) * inner);
    ctx.lineTo(globe.centerX + Math.cos(ang) * outer, globe.centerY + Math.sin(ang) * outer);
    ctx.strokeStyle = i % 9 === 0 ? "rgba(255,36,36,0.5)" : "rgba(255,255,255,0.2)";
    ctx.lineWidth = 1;
    ctx.stroke();
  }
}

function drawLinksAndNodes() {
  links.forEach(([from, to]) => {
    const a = project(nodes[from].lat, nodes[from].lon, globe.rotY);
    const b = project(nodes[to].lat, nodes[to].lon, globe.rotY);

    if (a.z < -85 || b.z < -85) {
      return;
    }

    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.quadraticCurveTo((a.x + b.x) / 2, Math.min(a.y, b.y) - 50, b.x, b.y);
    ctx.strokeStyle = "rgba(255,36,36,0.5)";
    ctx.lineWidth = 1.2;
    ctx.stroke();
  });

  nodes.forEach((node) => {
    const p = project(node.lat, node.lon, globe.rotY);
    if (p.z < -95) {
      return;
    }

    const main = node.name === "Bhagsar";
    ctx.beginPath();
    ctx.arc(p.x, p.y, main ? 5 : 3, 0, Math.PI * 2);
    ctx.fillStyle = main ? "#ff2424" : "#f1f5fa";
    ctx.shadowColor = main ? "rgba(255,36,36,0.9)" : "rgba(255,255,255,0.6)";
    ctx.shadowBlur = main ? 16 : 8;
    ctx.fill();
    ctx.shadowBlur = 0;

    if (main) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 12 + Math.sin(Date.now() * 0.008) * 2, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(255,36,36,0.5)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  });
}

function render() {
  ctx.clearRect(0, 0, globe.width, globe.height);
  drawTicks();
  drawSphere();
  drawGrid();
  drawLinksAndNodes();
  globe.rotY += 0.003;
  requestAnimationFrame(render);
}

fillMatrix(leftMatrix);
fillMatrix(rightMatrix);
animateBars();
initRings();
render();
