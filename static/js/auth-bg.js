/**
 * 宇宙海：斜穿银河涌浪海面 + 远景星空极光，双宇航员在星空层缓慢漂移
 */
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { clone as cloneSkinned } from "three/addons/utils/SkeletonUtils.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";

const MODEL_CANDIDATES = [
  "https://cdn.3dassets.dev/assets/39245/v1/model.glb",
  "https://cdn.3dassets.dev/assets/39246/v1/model.glb",
  "/static/models/auth-astronaut.glb",
];

const TIME_SCALE = 0.62;
const SEA_WAVE_RATE = 1.75;

function smoothstepJs(e0, e1, x) {
  const t = Math.max(0, Math.min(1, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
}

/** 小浪 + 略高浪峰：压低长涌，主风向碎浪与 bump 成形 — 与顶点着色器一致 */
function chopWaveSample(gx, gy, t) {
  const tt = t * SEA_WAVE_RATE;
  const wx = 0.88;
  const wy = -0.47;
  const along = wx * gx + wy * gy;
  const cross = -wy * gx + wx * gy;
  const distFar = 1 - smoothstepJs(18, -40, gy);
  const farK = smoothstepJs(0.08, 0.9, distFar);
  const swellK = 0.3 + farK * 0.34;
  const chopK = 0.26 + farK * 0.44;
  let h = 0;
  let hx = 0;
  let hy = 0;
  const addAlong = (amp, freq, phase, scale) => {
    const f = along * freq + phase;
    const s = Math.sin(f);
    const c = Math.cos(f);
    const a = amp * scale;
    h += a * s;
    hx += a * c * wx * freq;
    hy += a * c * wy * freq;
  };
  const addCross = (amp, freq, phase, scale) => {
    const f = cross * freq + phase;
    const s = Math.sin(f);
    const c = Math.cos(f);
    const a = amp * scale;
    h += a * s;
    hx += a * c * -wy * freq;
    hy += a * c * wx * freq;
  };
  addAlong(0.1, 0.08, tt * 0.028, swellK * 1.02);
  addAlong(0.13, 0.1, tt * 0.038, swellK);
  addAlong(0.15, 0.19, tt * 0.052, swellK * 0.95);
  addAlong(0.16, 0.26, tt * 0.06, chopK);
  addAlong(0.14, 0.34, tt * 0.072, chopK * 0.92);
  addAlong(0.11, 0.42, tt * 0.084, chopK * 0.78);
  addCross(0.07, 0.28, tt * 0.048, 0.3 + farK * 0.22);
  addCross(0.055, 0.36, tt * 0.065, 0.16 + farK * 0.32);
  const nearK = 1 - farK * 0.38;
  addAlong(0.13, 0.38, tt * 0.08, chopK * 0.72 * (0.45 + nearK * 0.75));
  const bumpK = 0.4 + farK * 0.48;
  const bump = Math.max(0, Math.sin(along * 0.32 + tt * 0.085));
  const bumpH = bump * bump * bumpK * (0.28 + nearK * 0.22);
  h += bumpH;
  const bump2 = Math.max(0, Math.sin(along * 0.21 - tt * 0.055 + cross * 0.08));
  const bumpH2 = bump2 * bump2 * bumpK * (0.12 + nearK * 0.1);
  h += bumpH2;
  const bumpD =
    2 * bump * Math.cos(along * 0.32 + tt * 0.085) * 0.32 * bumpK * (0.28 + nearK * 0.22) +
    2 * bump2 * Math.cos(along * 0.21 - tt * 0.055 + cross * 0.08) * 0.21 * bumpK * (0.12 + nearK * 0.1);
  hx += bumpD * wx;
  hy += bumpD * wy;
  return { h, hx, hy };
}

function waveHeight(gx, gy, t) {
  return chopWaveSample(gx, gy, t).h;
}

function waveSlope(x, z, t) {
  const s = chopWaveSample(x, z, t);
  return { h: s.h, hx: s.hx, hz: s.hy };
}

const seaVert = `
  uniform float uTime;
  uniform vec4 uRipples[6];
  varying vec2 vUv;
  varying float vWave;
  varying float vSteep;
  varying vec3 vWorldPos;
  varying vec3 vNormalW;
  varying float vFarPeak;
  void seaAlongWave(inout float h, inout float hx, inout float hy, float along, float wx, float wy, float amp, float freq, float ph, float sc) {
    float f = along * freq + ph;
    float s = sin(f);
    float c = cos(f);
    float a = amp * sc;
    h += a * s;
    hx += a * c * wx * freq;
    hy += a * c * wy * freq;
  }
  void seaCrossWave(inout float h, inout float hx, inout float hy, float cross, float wx, float wy, float amp, float freq, float ph, float sc) {
    float f = cross * freq + ph;
    float s = sin(f);
    float c = cos(f);
    float a = amp * sc;
    h += a * s;
    hx += a * c * (-wy) * freq;
    hy += a * c * wx * freq;
  }
  void main() {
    vec3 pos = position;
    float gx = pos.x;
    float gy = pos.y;
    float wt = uTime * 1.75;
    float wx = 0.88;
    float wy = -0.47;
    float along = wx * gx + wy * gy;
    float cross = -wy * gx + wx * gy;
    float distFar = 1.0 - smoothstep(18.0, -40.0, gy);
    float farK = smoothstep(0.08, 0.9, distFar);
    float swellK = 0.3 + farK * 0.34;
    float chopK = 0.26 + farK * 0.44;
    float h = 0.0;
    float hx = 0.0;
    float hy = 0.0;
    seaAlongWave(h, hx, hy, along, wx, wy, 0.1, 0.08, wt * 0.028, swellK * 1.02);
    seaAlongWave(h, hx, hy, along, wx, wy, 0.13, 0.1, wt * 0.038, swellK);
    seaAlongWave(h, hx, hy, along, wx, wy, 0.15, 0.19, wt * 0.052, swellK * 0.95);
    seaAlongWave(h, hx, hy, along, wx, wy, 0.16, 0.26, wt * 0.06, chopK);
    seaAlongWave(h, hx, hy, along, wx, wy, 0.14, 0.34, wt * 0.072, chopK * 0.92);
    seaAlongWave(h, hx, hy, along, wx, wy, 0.11, 0.42, wt * 0.084, chopK * 0.78);
    seaCrossWave(h, hx, hy, cross, wx, wy, 0.07, 0.28, wt * 0.048, 0.3 + farK * 0.22);
    seaCrossWave(h, hx, hy, cross, wx, wy, 0.055, 0.36, wt * 0.065, 0.16 + farK * 0.32);
    float nearK = 1.0 - farK * 0.38;
    seaAlongWave(h, hx, hy, along, wx, wy, 0.13, 0.38, wt * 0.08, chopK * 0.72 * (0.45 + nearK * 0.75));
    float bumpK = 0.4 + farK * 0.48;
    float bump = max(sin(along * 0.32 + wt * 0.085), 0.0);
    float bumpH = bump * bump * bumpK * (0.28 + nearK * 0.22);
    h += bumpH;
    float bump2 = max(sin(along * 0.21 - wt * 0.055 + cross * 0.08), 0.0);
    float bumpH2 = bump2 * bump2 * bumpK * (0.12 + nearK * 0.1);
    h += bumpH2;
    float bumpD =
      2.0 * bump * cos(along * 0.32 + wt * 0.085) * 0.32 * bumpK * (0.28 + nearK * 0.22) +
      2.0 * bump2 * cos(along * 0.21 - wt * 0.055 + cross * 0.08) * 0.21 * bumpK * (0.12 + nearK * 0.1);
    hx += bumpD * wx;
    hy += bumpD * wy;
    float farPeak = farK;
    float rippleH = 0.0;
    for(int i = 0; i < 6; i++) {
      vec4 rip = uRipples[i];
      if(rip.w < 0.01) continue;
      float age = uTime - rip.z;
      if(age > 7.5) continue;
      vec2 rd = vec2(gx, gy) - rip.xy;
      float dist = length(rd);
      float fade = smoothstep(7.5, 0.2, age);
      float waveR = (
        sin(dist * 1.48 - age * 2.65) * 0.65 +
        sin(dist * 2.25 - age * 3.9) * 0.38
      ) * exp(-dist * 0.082 - age * 0.38) * fade;
      rippleH += waveR * rip.w * 0.48;
    }
    h += rippleH;
    pos.z += h;
    vWave = h;
    vSteep = length(vec2(hx, hy));
    vFarPeak = farPeak;
    vec4 wp = modelMatrix * vec4(pos, 1.0);
    vWorldPos = wp.xyz;
    vNormalW = normalize(normalMatrix * vec3(-hx, -hy, 1.0));
    vUv = uv;
    gl_Position = projectionMatrix * viewMatrix * wp;
  }
`;

const auroraVert = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const auroraFrag = `
  uniform float uTime;
  uniform float uPhase;
  varying vec2 vUv;
  void main() {
    vec2 uv = vUv;
    float t = uTime + uPhase;
    float sway = sin(uv.x * 5.4 + t * 0.32) * 0.5 + 0.5;
    float veil = sin(uv.x * 9.5 - t * 0.48 + uv.y * 4.8) * sin(uv.y * 7.2 + t * 0.36);
    veil = veil * 0.5 + 0.5;
    float curtain = smoothstep(0.02, 0.78, uv.y) * (1.0 - smoothstep(0.88, 1.02, uv.y));
    curtain *= (0.45 + sway * 0.55) * (0.5 + veil * 0.5);
    vec3 aurGreen = vec3(0.04, 0.48, 0.3);
    vec3 aurCyan = vec3(0.08, 0.4, 0.55);
    vec3 aurViolet = vec3(0.28, 0.12, 0.46);
    vec3 col = mix(aurGreen, aurCyan, smoothstep(0.12, 0.55, uv.x + veil * 0.15));
    col = mix(col, aurViolet, smoothstep(0.48, 0.92, uv.x) * 0.62);
    float alpha = curtain * (0.2 + veil * 0.12);
    gl_FragColor = vec4(col * alpha, alpha);
  }
`;

const seaFrag = `
  uniform float uTime;
  uniform vec3 uCamera;
  uniform sampler2D uCosmicTex;
  uniform vec4 uRipples[6];
  varying vec2 vUv;
  varying float vWave;
  varying float vSteep;
  varying vec3 vWorldPos;
  varying vec3 vNormalW;
  varying float vFarPeak;
  float authRiverBand(vec2 wp, float vWave, float nWy, vec2 axis, float wCore, float wHalo, float alongW, float t) {
    float along = dot(wp, axis) + vWave * 1.25 * alongW;
    float across = dot(wp, vec2(-axis.y, axis.x));
    across += vWave * 0.52 + nWy * 1.25 + sin(along * 0.1 + t * 0.14) * 0.1;
    float core = exp(-across * across * wCore);
    float halo = exp(-across * across * wHalo);
    float r = core * 0.9 + halo * 0.22;
    r *= smoothstep(-48.0, -7.0, along) * smoothstep(48.0, 9.0, along);
    return clamp(r, 0.0, 1.0);
  }
  void main() {
    vec2 parallax = vNormalW.xz;
    vec2 milkyAxis = normalize(vec2(0.88, -0.47));
    vec2 seaDrift = milkyAxis * uTime * 0.0028 + vec2(vWave * 0.085, vSteep * 0.055);
    vec2 flowMid = vUv * vec2(5.8, 4.2) + vec2(uTime * 0.0088, uTime * 0.0062) + seaDrift;
    vec2 flowNear = vUv * vec2(9.5, 6.8) - vec2(uTime * 0.0058, uTime * 0.0068) + seaDrift * 1.15;
    flowMid += parallax * 0.038;
    flowNear += parallax * 0.055;
    vec3 midC = texture2D(uCosmicTex, flowMid).rgb;
    vec3 nearC = texture2D(uCosmicTex, flowNear).rgb;
    float lumMid = dot(midC, vec3(0.299, 0.587, 0.114));
    float lumNear = dot(nearC, vec3(0.299, 0.587, 0.114));
    float edgeMid = length(vec3(dFdx(lumMid), dFdy(lumMid), 0.0));
    float edgeNear = length(vec3(dFdx(lumNear), dFdy(lumNear), 0.0));
    float texSharp = smoothstep(0.01, 0.048, max(edgeMid, edgeNear) * 1.15);
    float softBlob = smoothstep(0.11, 0.34, lumMid) * (1.0 - texSharp);
    vec3 texDetail = mix(midC, nearC, 0.28) * texSharp;
  float ridge = smoothstep(-0.55, 1.15, vWave);
  float trough = 1.0 - ridge;
  float crest = smoothstep(-0.12, 0.32, vWave);
  float crestSharp = pow(crest, 0.26) * (0.62 + vFarPeak * 0.42);
  float peakGlint = smoothstep(-0.02, 0.32, vWave) * smoothstep(0.06, 0.65, vSteep) * (0.62 + vFarPeak * 0.38);
  float spikeShine = smoothstep(0.18, 0.82, vSteep) * crestSharp * 0.92;
  float waveLayer = smoothstep(-1.35, 0.2, vWave) * (1.0 - smoothstep(0.2, 1.55, vWave));
  float tierLo = smoothstep(-0.25, 0.38, vWave + vFarPeak * 0.28);
  float tierMid = smoothstep(0.12, 0.62, vWave + vFarPeak * 0.48);
  float tierHi = smoothstep(0.38, 1.05, vWave + vFarPeak * 0.72);
    vec3 texMix = mix(midC, nearC, 0.22);
    float tr = texMix.r;
    float tg = texMix.g;
    float tb = texMix.b;
    float lum = dot(texMix, vec3(0.299, 0.587, 0.114));
    float galaxyStruct = smoothstep(0.028, 0.17, lumMid) * texSharp;
    galaxyStruct *= (1.0 - smoothstep(0.55, 0.92, lumMid));
    float voidMask = smoothstep(0.055, 0.008, lum);
    float nebHint = smoothstep(0.1, 0.3, lum) * (1.0 - smoothstep(0.38, 0.62, lum));
    float hotR = smoothstep(0.12, 0.42, tr);
    float coolB = smoothstep(0.1, 0.38, tb);
    float warmBias = smoothstep(0.05, 0.28, tr - tb * 0.55) * nebHint;
    vec3 inkBlack = vec3(0.002, 0.002, 0.006);
    vec3 navyDepth = vec3(0.018, 0.038, 0.16);
    vec3 violetLiq = vec3(0.48, 0.14, 0.96);
    vec3 purpleLiq = vec3(0.62, 0.22, 1.0);
    vec3 magentaNeon = vec3(1.0, 0.1, 0.55);
    vec3 pinkBright = vec3(1.0, 0.2, 0.65);
    vec3 cyanElec = vec3(0.06, 0.88, 1.0);
    vec3 goldWarm = vec3(1.0, 0.5, 0.1);
    vec3 silverWhite = vec3(0.97, 0.98, 1.0);
    vec3 seaMag = vec3(1.02, 0.26, 0.58);
    vec3 seaVio = vec3(0.68, 0.28, 0.98);
    vec3 seaIce = vec3(0.42, 0.48, 0.95);
    vec3 waterAbyss = vec3(0.004, 0.028, 0.095);
    vec3 waterMid = vec3(0.02, 0.065, 0.165);
    vec3 waterShine = vec3(0.05, 0.12, 0.28);
    vec3 seaDeep = mix(inkBlack, waterAbyss, 0.9);
    vec3 seaShallow = mix(waterMid, waterShine, crestSharp * 0.62);
    vec3 tierTint = mix(seaDeep, waterMid, tierLo * 0.85);
    tierTint = mix(tierTint, waterShine, tierMid * 0.62);
    tierTint = mix(tierTint, mix(waterShine, cyanElec * 0.12, 0.35), tierHi * 0.5);
    vec3 col = mix(seaDeep, seaShallow, clamp(trough * 0.52 + crestSharp * 0.58 + vFarPeak * crestSharp * 0.2, 0.0, 1.0));
    col = mix(col, waterAbyss, trough * 0.32);
    vec2 riverA0 = normalize(vec2(0.88, -0.47));
    vec2 riverA1 = normalize(vec2(0.82, -0.57));
    vec2 riverA2 = normalize(vec2(0.92, -0.38));
    vec2 riverA3 = normalize(vec2(0.86, -0.52));
    vec2 riverA4 = normalize(vec2(0.9, -0.41));
    float r0 = authRiverBand(vWorldPos.xz, vWave, vNormalW.y, riverA0, 0.028, 0.009, 1.0, uTime);
    float r1 = authRiverBand(vWorldPos.xz, vWave, vNormalW.y, riverA1, 0.026, 0.0085, 0.94, uTime);
    float r2 = authRiverBand(vWorldPos.xz, vWave, vNormalW.y, riverA2, 0.027, 0.0088, 0.96, uTime);
    float r3 = authRiverBand(vWorldPos.xz, vWave, vNormalW.y, riverA3, 0.025, 0.0082, 0.92, uTime);
    float r4 = authRiverBand(vWorldPos.xz, vWave, vNormalW.y, riverA4, 0.024, 0.0078, 0.9, uTime);
    float milkyRiver = max(r0, max(r1 * 0.78, max(r2 * 0.74, max(r3 * 0.7, r4 * 0.68))));
    float milkyAlong = dot(vWorldPos.xz, riverA0) + vWave * 1.35;
    float offRiver = 1.0 - smoothstep(0.08, 0.42, milkyRiver);
    col = mix(col, tierTint, (0.22 + vFarPeak * 0.32) * (1.0 - milkyRiver * 0.22));
    vec3 riverTint0 = mix(vec3(0.5, 0.28, 0.95), silverWhite, 0.48);
    vec3 riverTint1 = mix(vec3(0.15, 0.52, 0.98), silverWhite, 0.42);
    vec3 riverTint2 = mix(vec3(0.95, 0.32, 0.62), silverWhite, 0.4);
    vec3 riverTint3 = mix(vec3(0.98, 0.22, 0.55), silverWhite, 0.38);
    vec3 riverTint4 = mix(vec3(0.3, 0.34, 0.92), silverWhite, 0.4);
    float wSum = r0 + r1 * 0.78 + r2 * 0.74 + r3 * 0.7 + r4 * 0.68 + 0.001;
    vec3 riverTint = (riverTint0 * r0 + riverTint1 * r1 * 0.78 + riverTint2 * r2 * 0.74
                    + riverTint3 * r3 * 0.7 + riverTint4 * r4 * 0.68) / wSum;
    vec3 texHue = texMix * (1.35 + milkyRiver * 0.55);
    float clusterMask = smoothstep(0.05, 0.26, lum) * (1.0 - voidMask) * texSharp;
    clusterMask *= (0.35 + milkyRiver * 0.75);
    col += texHue * clusterMask * 0.72;
    vec3 milkyOnSea = texDetail * (0.42 + milkyRiver * 0.88);
    col += milkyOnSea * (0.12 + milkyRiver * 0.62) * riverTint;
    col = mix(col, inkBlack, offRiver * 0.34);
    float cosmicPatch = galaxyStruct * (1.0 - milkyRiver * 0.12);
    float hueSeed = fract(tr * 2.35 + tg * 1.15 - tb * 0.85 + vUv.x * 0.17);
    vec3 cMag = vec3(1.02, 0.3, 0.58);
    vec3 cVio = vec3(0.6, 0.34, 1.0);
    vec3 cCyan = vec3(0.28, 0.62, 1.02);
    vec3 cRose = vec3(0.98, 0.45, 0.72);
    vec3 cIndigo = vec3(0.36, 0.38, 0.9);
    vec3 cosmicHue = mix(cMag, cVio, smoothstep(0.02, 0.24, hueSeed));
    cosmicHue = mix(cosmicHue, cCyan, smoothstep(0.22, 0.46, hueSeed));
    cosmicHue = mix(cosmicHue, cRose, smoothstep(0.42, 0.66, hueSeed));
    cosmicHue = mix(cosmicHue, cIndigo, smoothstep(0.64, 0.88, hueSeed));
    col += texDetail * cosmicPatch * cosmicHue * (0.42 + milkyRiver * 0.82);
    col += texDetail * galaxyStruct * milkyRiver * mix(cosmicHue, riverTint, 0.55) * 0.52;
    col += texHue * galaxyStruct * 0.38 * (1.0 - softBlob * 0.35);
    col *= 1.0 - softBlob * 0.65 * (1.0 - milkyRiver * 0.55);
    col += vec3(0.32, 0.26, 0.48) * milkyRiver * voidMask * 0.09;
    vec3 purpleLayer = violetLiq * coolB * 1.05 + purpleLiq * nebHint;
    col = mix(col, col + purpleLayer * 0.38, (1.0 - voidMask) * nebHint * 0.32 * (1.0 - galaxyStruct * 0.92) * offRiver);
    vec3 pinkLayer = magentaNeon * hotR * 0.45 + pinkBright * (crestSharp * 0.32 + hotR * 0.18);
    col += pinkLayer * (1.0 - voidMask * 0.55) * 0.22 * offRiver;
    col += texDetail * nebHint * (0.28 + milkyRiver * 0.55);
    float vioW = smoothstep(0.08, 0.42, tr - tb * 0.3);
    float iceW = smoothstep(0.12, 0.38, tb) * (1.0 - smoothstep(0.45, 0.85, tr));
    vec3 seaHue = mix(mix(seaMag, seaVio, vioW), seaIce, iceW * 0.32);
    float darkCosmos = voidMask * 0.62 + (1.0 - nebHint) * 0.3;
    col += texDetail * seaHue * darkCosmos * 0.1 * mix(vec3(1.0), cosmicHue, cosmicPatch * 0.65);
    col += mix(waterMid, cyanElec * 0.42, 0.55) * crestSharp * (0.14 + coolB * 0.16);
    col += mix(waterShine, cyanElec * 0.25, 0.45) * waveLayer * 0.17;
    col += violetLiq * milkyRiver * crestSharp * 0.05;
    vec3 peakTint = mix(pinkBright * 0.92, cyanElec * 0.55, 0.38);
    float shoreNear = smoothstep(6.0, 22.0, length(vWorldPos.xz - uCamera.xz));
    col += peakTint * (peakGlint * 0.22 + spikeShine * 0.14) * mix(0.55, 1.0, shoreNear);
    col += mix(pinkBright * 0.35, violetLiq * 0.28, coolB) * warmBias * 0.1;
    col += magentaNeon * smoothstep(0.55, 0.85, lum) * 0.035;
    col = mix(col, inkBlack, voidMask * 0.62);
    col = mix(col, navyDepth * 0.35, (1.0 - nebHint) * 0.28);
    vec2 wpCam = vWorldPos.xz - uCamera.xz;
    float horizonDepth = smoothstep(6.0, 52.0, length(wpCam));
    float mtSil = smoothstep(-0.15, 0.72, vWave) * vFarPeak * horizonDepth;
    col = mix(col, col * 0.68 + seaShallow * 0.42, mtSil * 0.48);
    col = mix(col, mix(inkBlack, navyDepth, 0.75), horizonDepth * 0.42);
    float starStream = sin(vWorldPos.x * 0.38 + vWorldPos.z * 0.29 + uTime * 0.65) * 0.5 + 0.5;
    vec2 starUvA = vWorldPos.xz * 3.35 + vUv * 26.0 + vec2(uTime * 0.014, -uTime * 0.01);
    starUvA += milkyAxis * uTime * 0.006;
    vec2 starFA = fract(starUvA) - 0.5;
    float starHashA = fract(sin(dot(floor(starUvA), vec2(127.1, 311.7))) * 43758.5453);
    float starDense = 0.87 - milkyRiver * 0.22 + starStream * 0.02 - crestSharp * 0.06;
    float pinA = step(starDense, starHashA) * (1.0 - step(0.052, length(starFA)));
    float tintA = fract(starHashA * 17.3);
    vec3 colA = mix(silverWhite * 0.62, cyanElec * 0.45, step(0.45, tintA));
    colA = mix(colA, goldWarm * 0.35, step(0.82, tintA) * step(0.35, milkyRiver));
    vec3 starGlow = colA * pinA * (0.05 + fract(starHashA * 9.1) * 0.06) * (0.35 + milkyRiver * 0.75) * (0.45 + crestSharp * 0.55);
    vec2 starUvB = vWorldPos.xz * 5.1 + vUv * 34.0 + vec2(uTime * 0.008, uTime * 0.005);
    vec2 starFB = fract(starUvB) - 0.5;
    float starHashB = fract(sin(dot(floor(starUvB), vec2(83.1, 57.7))) * 22458.5453);
    float pinB = step(0.86 - milkyRiver * 0.09, starHashB) * (1.0 - step(0.038, length(starFB)));
    starGlow += mix(pinkBright * 0.45, violetLiq * 0.42, step(0.5, fract(starHashB * 7.3))) * pinB * (0.045 + milkyRiver * 0.04);
    vec2 wp = vWorldPos.xz;
    float ripA = sin(wp.x * 1.35 + uTime * 0.42) * sin(wp.y * 1.1 + uTime * 0.36);
    float ripB = sin(dot(wp, vec2(0.82, 0.58)) * 2.4 - uTime * 0.52);
    float ripC = cos(wp.x * 0.65 - wp.y * 0.7 + uTime * 0.3);
    float ripple = ripA * 0.45 + ripB * 0.35 + ripC * 0.25;
    ripple = ripple * 0.5 + 0.5;
    col += cyanElec * ripple * trough * 0.04 * offRiver;
    col += magentaNeon * ripple * trough * 0.02 * offRiver;
    col += cyanElec * pow(ripple, 4.0) * crest * 0.03;
    float vein = smoothstep(0.12, 0.55, vSteep) * crestSharp * smoothstep(0.35, 0.88, milkyRiver);
    col += goldWarm * vein * (0.06 + sin(milkyAlong * 0.22 + uTime * 0.4) * 0.02);
    col += mix(pinkBright, magentaNeon, 0.35) * crestSharp * 0.025 * offRiver;
    col += magentaNeon * waveLayer * nebHint * 0.08;
    col = mix(col, inkBlack, pow(trough, 1.1) * 0.58);
    vec3 n = normalize(vNormalW);
    vec3 viewDir = normalize(uCamera - vWorldPos);
    vec3 lightDir = normalize(vec3(-0.35, 1.0, 0.35));
    float diff = max(dot(n, lightDir), 0.0);
    float steep = clamp(1.0 - n.y, 0.0, 1.0);
    float slopeShade = 0.48 + steep * 0.46 - abs(vWave) * 0.028;
    col *= (0.26 + diff * 0.38 + crestSharp * 0.18) * slopeShade;
    col = mix(col, seaShallow, crestSharp * (1.0 - milkyRiver * 0.32) * 0.26);
    col = mix(col, col * 0.32, steep * trough * 0.65);
    vec3 halfDir = normalize(lightDir + viewDir);
    float specTight = pow(max(dot(n, halfDir), 0.0), 196.0);
    col += pinkBright * specTight * (0.008 + crestSharp * 0.04 + peakGlint * 0.03);
    col += cyanElec * specTight * (crestSharp * 0.04 + peakGlint * 0.035);
    float fres = pow(1.0 - max(dot(n, viewDir), 0.0), 2.8);
    col += mix(cyanElec * 0.45, waterShine, crestSharp) * fres * (0.035 + peakGlint * 0.04);
    float horizonAurora = horizonDepth * smoothstep(0.55, 0.92, 1.0 - n.y);
    vec3 auroraRef = mix(vec3(0.06, 0.32, 0.24), vec3(0.22, 0.12, 0.42), sin(uTime * 0.38 + vWorldPos.x * 0.08) * 0.5 + 0.5);
    col += auroraRef * horizonAurora * 0.09;
    float luma = dot(col, vec3(0.299, 0.587, 0.114));
    float bleach = smoothstep(0.68, 1.15, luma);
    vec3 toned = col / (col + vec3(0.42));
    vec3 chromaHi = mix(pinkBright * luma, cyanElec * luma * 0.65, 0.35)
                  + violetLiq * luma * 0.22;
    col = mix(col, mix(toned, chromaHi, 0.32), bleach * 0.75);
    float grey = dot(col, vec3(0.299, 0.587, 0.114));
    col = mix(vec3(grey), col, mix(0.78, 0.95, nebHint + crestSharp * 0.35));
    col = mix(inkBlack, col, 0.94);
    float starVis = (0.28 + voidMask * 0.72 + horizonDepth * 0.12) * (1.0 - softBlob * 0.85);
    col += starGlow * starVis;
    float interactRing = 0.0;
    float interactCrest = 0.0;
    for(int i = 0; i < 6; i++) {
      vec4 rip = uRipples[i];
      if(rip.w < 0.001) continue;
      float age = uTime - rip.z;
      if(age > 7.2) continue;
      vec2 rd = vWorldPos.xz - rip.xy;
      float dist = length(rd);
      float fade = smoothstep(7.2, 0.15, age);
      float waveI = (
        sin(dist * 1.5 - age * 2.7) * 0.66 +
        sin(dist * 2.2 - age * 4.0) * 0.4
      ) * exp(-dist * 0.082 - age * 0.36) * fade;
      interactRing += waveI * rip.w;
      interactCrest += abs(waveI) * rip.w * exp(-age * 0.2);
    }
    col += mix(cyanElec, pinkBright, 0.38) * interactRing * 0.12;
    col += magentaNeon * interactCrest * 0.06;
    gl_FragColor = vec4(col, 1.0);
  }
`;

function spiralArmXY(phase, t, R, wave) {
  const theta = phase + t * 3.05 * Math.PI + Math.sin(t * 8.0 + phase) * (wave ?? 0.08);
  const rr = R * 0.055 * Math.exp(t * 2.62);
  return [Math.cos(theta) * rr, Math.sin(theta) * rr];
}

function paintGalaxyArmStars(ctx, R, arms, phase, rand, palette, dense) {
  const mult = dense ? 1.55 : 1;
  const n = Math.min(520, (70 + (R * R * 0.11) | 0) * mult);
  ctx.globalCompositeOperation = "lighter";
  for (let i = 0; i < n; i++) {
    const arm = rand() * arms | 0;
    const t = 0.04 + rand() * 0.9;
    const jitter = (rand() - 0.5) * R * 0.042 * (0.28 + t);
    const p = (arm * Math.PI * 2) / arms + phase;
    const [sx, sy] = spiralArmXY(p, t, R, 0.06);
    const px = sx + Math.cos(p + t) * jitter;
    const py = sy + Math.sin(p + t) * jitter;
    if (Math.hypot(px, py) > R * 0.96) continue;
    const roll = rand();
    const a = 0.32 + rand() * 0.55;
  let c =
      roll < 0.62
        ? `rgba(235,228,255,${a})`
        : roll < 0.85
          ? palette.armBright || palette.arm
          : palette.core;
    ctx.fillStyle = c;
    ctx.fillRect(px, py, 1, 1);
  }
  ctx.globalCompositeOperation = "source-over";
}

function paintArmBrightNodes(ctx, R, arms, phase, rand, palette) {
  const nodes = 5 + (R * 0.1) | 0;
  ctx.globalCompositeOperation = "lighter";
  for (let arm = 0; arm < arms; arm++) {
    const p = (arm * Math.PI * 2) / arms + phase;
    for (let n = 0; n < nodes; n++) {
      const t = 0.14 + (n / Math.max(1, nodes)) * 0.76 + rand() * 0.03;
      const [px, py] = spiralArmXY(p, t, R, 0.04);
      const m = 3 + (rand() * 4) | 0;
      for (let k = 0; k < m; k++) {
        ctx.globalAlpha = 0.38 + rand() * 0.38;
        ctx.fillStyle = k === 0 ? palette.core : palette.armBright;
        ctx.fillRect(
          px + (rand() - 0.5) * R * 0.018,
          py + (rand() - 0.5) * R * 0.018,
          1,
          1
        );
      }
    }
  }
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = "source-over";
}

function paintGalaxyDustLanes(ctx, R, arms, phase, rand) {
  ctx.globalCompositeOperation = "darken";
  for (let arm = 0; arm < arms; arm++) {
    const p = (arm * Math.PI * 2) / arms + phase + 0.26;
    ctx.strokeStyle = "rgba(2,1,8,0.72)";
    ctx.lineWidth = Math.max(1.2, R * 0.045);
    ctx.lineCap = "round";
    ctx.beginPath();
    let started = false;
    for (let i = 0; i <= 110; i++) {
      const t = i / 110;
      const [px, py] = spiralArmXY(p, t, R, -0.05);
      if (Math.hypot(px, py) > R * 0.9) break;
      if (!started) {
        ctx.moveTo(px, py);
        started = true;
      } else ctx.lineTo(px, py);
    }
    ctx.stroke();
  }
  for (let k = 0; k < 3 + (rand() * 4 | 0); k++) {
    const bx = (rand() - 0.5) * R * 1.2;
    const by = (rand() - 0.5) * R * 0.35;
    const bw = R * (0.08 + rand() * 0.14);
    const bh = R * (0.02 + rand() * 0.05);
    ctx.fillStyle = `rgba(0,0,6,${0.35 + rand() * 0.35})`;
    ctx.beginPath();
    ctx.ellipse(bx, by, bw, bh, rand() * Math.PI, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalCompositeOperation = "source-over";
}

function paintFaceOnGalaxy(ctx, cx, cy, R, palette, rand, opts) {
  const tilt = opts?.tilt ?? 0.68 + rand() * 0.24;
  const arms = opts?.arms ?? 2 + (rand() * 2 | 0);
  const barred = opts?.barred ?? rand() < 0.32;
  const rot = opts?.rot ?? rand() * Math.PI * 2;
  const phase = opts?.phase ?? rand() * Math.PI * 2;
  const structureOnly = opts?.structureOnly ?? R > 36;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(rot);
  ctx.scale(1, tilt);
  ctx.beginPath();
  ctx.arc(0, 0, R, 0, Math.PI * 2);
  ctx.clip();
  if (!structureOnly) {
    const disc = ctx.createRadialGradient(0, 0, 0, 0, 0, R);
    disc.addColorStop(0, palette.mid);
    disc.addColorStop(0.22, "rgba(3,4,14,0.08)");
    disc.addColorStop(1, "transparent");
    ctx.globalAlpha = 0.35;
    ctx.fillStyle = disc;
    ctx.fillRect(-R, -R, R * 2, R * 2);
    ctx.globalAlpha = 1;
  }
  ctx.globalCompositeOperation = "lighter";
  if (structureOnly) {
    const coreN = 6 + (R * 0.06) | 0;
    for (let i = 0; i < coreN; i++) {
      const ox = (rand() - 0.5) * 4;
      const oy = (rand() - 0.5) * 4;
      ctx.fillStyle = i < 2 ? palette.core : palette.armBright;
      ctx.fillRect(ox, oy, 1, 1);
    }
  } else {
    const bulgeR = R * 0.11;
    const bulge = ctx.createRadialGradient(0, 0, 0, 0, 0, bulgeR);
    bulge.addColorStop(0, palette.bulge || palette.core);
    bulge.addColorStop(0.55, palette.mid);
    bulge.addColorStop(1, "transparent");
    ctx.globalAlpha = 0.55;
    ctx.fillStyle = bulge;
    ctx.beginPath();
    ctx.arc(0, 0, bulgeR, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
  }
  if (barred) {
    const barL = R * 0.44;
    if (structureOnly) {
      ctx.strokeStyle = palette.mid;
      ctx.lineWidth = Math.max(1, R * 0.03);
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(-barL, 0);
      ctx.lineTo(barL, 0);
      ctx.stroke();
      ctx.strokeStyle = palette.core;
      ctx.lineWidth = Math.max(0.8, R * 0.018);
      ctx.stroke();
    } else {
      const barW = R * 0.06;
      const barG = ctx.createLinearGradient(-barL, 0, barL, 0);
      barG.addColorStop(0, "transparent");
      barG.addColorStop(0.5, palette.core);
      barG.addColorStop(1, "transparent");
      ctx.fillStyle = barG;
      ctx.beginPath();
      ctx.ellipse(0, 0, barL, barW, 0, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  const darkArmW = structureOnly ? R * 0.055 : R * 0.1;
  const brightArmW = structureOnly ? R * 0.022 : R * 0.034;
  for (let arm = 0; arm < arms; arm++) {
    const p = (arm * Math.PI * 2) / arms + phase + (barred ? 0.18 : 0);
    ctx.strokeStyle = palette.dust || "rgba(8,4,18,0.5)";
    ctx.lineWidth = Math.max(2.0, darkArmW);
    ctx.lineCap = "round";
    ctx.beginPath();
    let started = false;
    for (let i = 0; i <= 150; i++) {
      const t = i / 150;
      const [px, py] = spiralArmXY(p, t, R, 0.04);
      if (Math.hypot(px, py) > R * 0.94) break;
      if (!started) {
        ctx.moveTo(px, py);
        started = true;
      } else ctx.lineTo(px, py);
    }
    ctx.stroke();
    ctx.strokeStyle = palette.armBright || palette.arm;
    ctx.lineWidth = Math.max(0.8, brightArmW);
    ctx.beginPath();
    started = false;
    for (let i = 0; i <= 150; i++) {
      const t = i / 150;
      const [px, py] = spiralArmXY(p, t, R, 0.06);
      if (Math.hypot(px, py) > R * 0.94) break;
      if (!started) {
        ctx.moveTo(px, py);
        started = true;
      } else ctx.lineTo(px, py);
    }
    ctx.stroke();
  }
  paintArmBrightNodes(ctx, R, arms, phase, rand, palette);
  paintGalaxyArmStars(ctx, R, arms, phase, rand, palette, structureOnly);
  paintGalaxyDustLanes(ctx, R, arms, phase, rand);
  ctx.globalCompositeOperation = "source-over";
  ctx.restore();
}

function paintStarCluster(ctx, cx, cy, rand) {
  const n = 4 + ((rand() * 5) | 0);
  for (let i = 0; i < n; i++) {
    paintPinStar(ctx, cx + (rand() - 0.5) * 9, cy + (rand() - 0.5) * 9, rand);
  }
}

function paintCosmicFilament(ctx, x0, y0, x1, y1, rand) {
  const w = 0.6 + rand() * 1.4;
  const ctrlX = (x0 + x1) * 0.5 + (rand() - 0.5) * 40;
  const ctrlY = (y0 + y1) * 0.5 + (rand() - 0.5) * 40;
  const hues = [
    "rgba(200,70,150,0.11)",
    "rgba(130,80,210,0.1)",
    "rgba(60,150,220,0.09)",
    "rgba(230,120,180,0.1)",
    "rgba(90,100,200,0.09)",
  ];
  ctx.strokeStyle = hues[(rand() * hues.length) | 0];
  ctx.lineWidth = w;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(x0, y0);
  ctx.quadraticCurveTo(ctrlX, ctrlY, x1, y1);
  ctx.stroke();
}

function paintPinStar(ctx, x, y, rand, palette) {
  const a = 0.28 + rand() * 0.48;
  let c;
  const roll = rand();
  if (palette && roll < 0.72) {
    c = roll < 0.38 ? palette.armBright : roll < 0.62 ? palette.core : palette.bulge;
  } else if (roll < 0.38) c = `rgba(238,236,255,${a})`;
  else if (roll < 0.58) c = `rgba(220,165,215,${a * 0.92})`;
  else if (roll < 0.76) c = `rgba(175,200,255,${a * 0.9})`;
  else if (roll < 0.9) c = `rgba(255,195,220,${a * 0.88})`;
  else c = `rgba(200,185,255,${a * 0.86})`;
  ctx.fillStyle = c;
  ctx.fillRect(x, y, 1, 1);
}

function nebulaStopsFromPalette(pal) {
  return [
    [0, pal.core],
    [0.42, pal.mid],
    [1, "transparent"],
  ];
}

/** 同色星系团：一团内共享配色，团与团彼此不同 */
function paintCosmicGalaxyCluster(ctx, cx, cy, palette, rand) {
  const stainR = 44 + rand() * 52;
  ctx.globalCompositeOperation = "lighter";
  const stain = ctx.createRadialGradient(cx, cy, 0, cx, cy, stainR);
  stain.addColorStop(0, palette.bulge);
  stain.addColorStop(0.38, palette.arm);
  stain.addColorStop(0.72, palette.mid);
  stain.addColorStop(1, "transparent");
  ctx.fillStyle = stain;
  ctx.beginPath();
  ctx.ellipse(cx, cy, stainR, stainR * (0.42 + rand() * 0.28), rand() * Math.PI, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalCompositeOperation = "source-over";
  paintNebulaWisp(ctx, cx, cy, 16 + rand() * 28, 0.48 + rand() * 0.28, nebulaStopsFromPalette(palette), rand);
  const nG = 2 + ((rand() * 2.5) | 0);
  for (let i = 0; i < nG; i++) {
    const ox = (rand() - 0.5) * 34;
    const oy = (rand() - 0.5) * 28;
    const r = 9 + rand() * 17;
    const pick = rand();
    if (pick < 0.52) {
      paintFaceOnGalaxy(ctx, cx + ox, cy + oy, r, palette, rand, { arms: 2, structureOnly: true });
    } else if (pick < 0.78) {
      paintEllipticalGalaxy(ctx, cx + ox, cy + oy, r * 0.72, palette, rand);
    } else if (pick < 0.92) {
      paintEdgeOnGalaxy(ctx, cx + ox, cy + oy, r, palette, rand);
    } else {
      paintRingGalaxy(ctx, cx + ox, cy + oy, r * 0.82, palette, rand);
    }
  }
  for (let i = 0; i < 4 + ((rand() * 4) | 0); i++) {
    paintPinStar(ctx, cx + (rand() - 0.5) * 24, cy + (rand() - 0.5) * 20, rand, palette);
  }
  paintStarCluster(ctx, cx + (rand() - 0.5) * 10, cy + (rand() - 0.5) * 8, rand);
}

function paintRingGalaxy(ctx, cx, cy, R, palette, rand) {
  const tilt = 0.55 + rand() * 0.3;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(rand() * Math.PI);
  ctx.scale(1, tilt);
  ctx.strokeStyle = palette.armBright || palette.arm;
  ctx.lineWidth = Math.max(1.2, R * 0.09);
  ctx.globalAlpha = 0.75;
  ctx.beginPath();
  ctx.ellipse(0, 0, R * 0.82, R * 0.82, 0, 0, Math.PI * 2);
  ctx.stroke();
  ctx.lineWidth = Math.max(0.6, R * 0.035);
  ctx.strokeStyle = palette.core;
  ctx.beginPath();
  ctx.ellipse(0, 0, R * 0.58, R * 0.58, 0, 0, Math.PI * 2);
  ctx.stroke();
  ctx.globalAlpha = 1;
  const coreR = R * 0.08;
  const g = ctx.createRadialGradient(0, 0, 0, 0, 0, coreR);
  g.addColorStop(0, palette.core);
  g.addColorStop(1, "transparent");
  ctx.globalAlpha = 0.75;
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(0, 0, coreR, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalAlpha = 1;
  paintGalaxyArmStars(ctx, R * 0.75, 2, rand() * Math.PI, rand, palette, true);
  ctx.restore();
}

function milkyBandFactor(x, y, S, angle, halfW) {
  const cx = S * 0.5;
  const cy = S * 0.5;
  const dx = x - cx;
  const dy = y - cy;
  const ca = Math.cos(angle);
  const sa = Math.sin(angle);
  const across = -dx * sa + dy * ca;
  const along = dx * ca + dy * sa;
  const w = halfW * (0.85 + Math.exp(-Math.abs(along) / (S * 0.42)) * 0.35);
  const gauss = Math.exp(-(across * across) / (w * w * 0.5));
  const alongMask = smoothstepJs(-S * 0.78, -S * 0.12, along) * smoothstepJs(S * 0.78, S * 0.12, along);
  return gauss * alongMask;
}

function paintMilkySpiralHints(ctx, len, halfW, phase, palette, rand) {
  ctx.globalCompositeOperation = "lighter";
  for (let arm = 0; arm < 2; arm++) {
    const p = phase + arm * Math.PI;
    ctx.strokeStyle = palette.armBright;
    ctx.globalAlpha = 0.35;
    ctx.lineWidth = 1;
    ctx.beginPath();
    let started = false;
    for (let i = 0; i <= 120; i++) {
      const t = i / 120;
      const theta = p + t * 2.4 * Math.PI;
      const rr = len * 0.04 * Math.exp(t * 2.1);
      const px = Math.cos(theta) * rr;
      const py = Math.sin(theta) * rr * 0.22;
      if (Math.abs(py) > halfW * 1.8) break;
      if (!started) {
        ctx.moveTo(px, py);
        started = true;
      } else ctx.lineTo(px, py);
    }
    ctx.stroke();
  }
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = "source-over";
}

function paintMilkyWayBand(ctx, S, rand, palette, opts) {
  const angle = opts?.angle ?? -0.38;
  const ox = (opts?.cx ?? 0.5) * S;
  const oy = (opts?.cy ?? 0.5) * S;
  const spread = opts?.spread ?? 1;
  const starN = opts?.stars ?? 5200;
  ctx.save();
  ctx.translate(ox, oy);
  ctx.rotate(angle);
  const len = S * 1.52 * spread;
  const halfW = S * 0.1 * spread;
  ctx.globalCompositeOperation = "darken";
  for (let i = 0; i < 22; i++) {
    const dx = (rand() - 0.5) * len * 0.96;
    const dy = (rand() - 0.5) * halfW * 1.6;
    ctx.fillStyle = `rgba(0,0,4,${0.3 + rand() * 0.35})`;
    ctx.beginPath();
    ctx.ellipse(dx, dy, 6 + rand() * 22, 1.5 + rand() * 4, rand() * Math.PI, 0, Math.PI * 2);
    ctx.fill();
  }
  paintMilkySpiralHints(ctx, len, halfW, rand() * Math.PI, palette, rand);
  ctx.globalCompositeOperation = "lighter";
  const starPalettes = ["magenta", "violet", "cyan", "rose", "indigo"];
  for (let i = 0; i < starN; i++) {
    const dx = (rand() - 0.5) * len;
    const bandT = Math.exp(-Math.abs(rand() - 0.5) * 2.1);
    const dy = (rand() - 0.5) * halfW * 2.65 * bandT;
    const a = 0.14 + rand() * 0.38;
    const pal = cosmicPaletteByKey(starPalettes[(rand() * starPalettes.length) | 0]);
    const roll = rand();
    if (roll < 0.38) ctx.fillStyle = `rgba(232,226,255,${a})`;
    else if (roll < 0.58) ctx.fillStyle = pal.armBright;
    else if (roll < 0.78) ctx.fillStyle = pal.core;
    else if (roll < 0.92) ctx.fillStyle = pal.bulge;
    else ctx.fillStyle = palette.armBright;
    ctx.fillRect(dx, dy, 1, 1);
  }
  for (let i = 0; i < 12; i++) {
    const dx = (rand() - 0.5) * len * 0.35;
    ctx.fillStyle = palette.core;
    ctx.fillRect(dx, (rand() - 0.5) * halfW * 0.4, 1, 1);
  }
  ctx.globalCompositeOperation = "source-over";
  ctx.restore();
}

function paintMilkyStarOcean(ctx, S, n, rand, bands) {
  for (let i = 0; i < n; i++) {
    const x = rand() * S;
    const y = rand() * S;
    let w = 0.22;
    for (const b of bands) {
      w += milkyBandFactor(x, y, S, b.angle, S * b.half) * b.weight;
    }
    if (rand() > Math.min(0.96, w)) continue;
    paintPinStar(ctx, x, y, rand);
  }
}

function paintEdgeOnGalaxy(ctx, cx, cy, L, palette, rand) {
  const ang = rand() * Math.PI;
  const thick = L * (0.09 + rand() * 0.06);
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(ang);
  ctx.strokeStyle = palette.arm;
  ctx.lineWidth = Math.max(1, thick * 0.9);
  ctx.globalAlpha = 0.5;
  ctx.beginPath();
  ctx.ellipse(0, 0, L, thick, 0, 0, Math.PI * 2);
  ctx.stroke();
  ctx.lineWidth = Math.max(0.6, thick * 0.28);
  ctx.strokeStyle = palette.armBright;
  ctx.stroke();
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = "darken";
  ctx.fillStyle = "rgba(0,0,6,0.62)";
  ctx.beginPath();
  ctx.ellipse(0, 0, L * 0.9, thick * 0.32, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalCompositeOperation = "lighter";
  for (let i = 0; i < 8; i++) {
    const ox = (rand() - 0.5) * L * 0.08;
    ctx.fillStyle = palette.core;
    ctx.fillRect(ox, 0, 1, 1);
  }
  const n = 45 + (rand() * 40 | 0);
  for (let i = 0; i < n; i++) {
    const t = rand() * 2 - 1;
    const y = (rand() - 0.5) * thick * 1.35;
    const a = 0.25 + rand() * 0.5;
    ctx.fillStyle = `rgba(235,240,255,${a})`;
    ctx.fillRect(t * L, y, 1, 1);
  }
  ctx.globalCompositeOperation = "source-over";
  ctx.restore();
}

function paintEllipticalGalaxy(ctx, cx, cy, R, palette, rand) {
  const tilt = 0.45 + rand() * 0.35;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(rand() * Math.PI);
  ctx.scale(1, tilt);
  ctx.strokeStyle = palette.arm;
  ctx.lineWidth = Math.max(0.8, R * 0.06);
  ctx.globalAlpha = 0.55;
  ctx.beginPath();
  ctx.ellipse(0, 0, R, R * 0.82, 0, 0, Math.PI * 2);
  ctx.stroke();
  ctx.lineWidth = Math.max(0.5, R * 0.022);
  ctx.strokeStyle = palette.armBright;
  ctx.stroke();
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = "lighter";
  const n = 35 + (rand() * 50 | 0);
  for (let i = 0; i < n; i++) {
    const th = rand() * Math.PI * 2;
    const rr = Math.sqrt(rand()) * R * 0.95;
    ctx.fillStyle = rand() < 0.65 ? `rgba(240,245,255,${0.2 + rand() * 0.45})` : palette.armBright;
    ctx.fillRect(Math.cos(th) * rr, Math.sin(th) * rr, 1, 1);
  }
  ctx.globalCompositeOperation = "source-over";
  ctx.restore();
}

function paintNebulaWisp(ctx, cx, cy, radius, flatness, stops, rand) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(rand() * Math.PI * 2);
  ctx.scale(1, flatness);
  const g = ctx.createRadialGradient(0, 0, 0, 0, 0, radius);
  stops.forEach(([t, c]) => g.addColorStop(t, c));
  ctx.globalCompositeOperation = "source-over";
  ctx.globalAlpha = 0.38;
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(0, 0, radius, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.restore();
}

function seaTextureRand(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pickCosmicPalette(rand) {
  const r = rand();
  if (r < 0.26) return "magenta";
  if (r < 0.5) return "violet";
  if (r < 0.72) return "cyan";
  if (r < 0.88) return "rose";
  return "indigo";
}

function cosmicPaletteByKey(key) {
  const table = {
    magenta: {
      core: "rgba(255,95,178,0.34)",
      bulge: "rgba(255,150,200,0.3)",
      arm: "rgba(150,48,120,0.2)",
      armBright: "rgba(235,105,185,0.33)",
      mid: "rgba(72,22,58,0.15)",
      dust: "rgba(5,2,10,0.8)",
    },
    violet: {
      core: "rgba(195,125,255,0.33)",
      bulge: "rgba(210,165,255,0.3)",
      arm: "rgba(88,50,168,0.18)",
      armBright: "rgba(165,112,240,0.32)",
      mid: "rgba(42,22,88,0.14)",
      dust: "rgba(4,3,12,0.78)",
    },
    cyan: {
      core: "rgba(120,210,255,0.32)",
      bulge: "rgba(150,225,255,0.28)",
      arm: "rgba(40,100,175,0.17)",
      armBright: "rgba(85,175,235,0.3)",
      mid: "rgba(15,40,95,0.13)",
      dust: "rgba(2,6,14,0.76)",
    },
    rose: {
      core: "rgba(255,165,195,0.33)",
      bulge: "rgba(255,190,210,0.29)",
      arm: "rgba(180,70,125,0.17)",
      armBright: "rgba(255,130,175,0.31)",
      mid: "rgba(85,30,55,0.13)",
      dust: "rgba(6,2,8,0.77)",
    },
    indigo: {
      core: "rgba(130,145,255,0.31)",
      bulge: "rgba(165,175,255,0.28)",
      arm: "rgba(55,65,155,0.16)",
      armBright: "rgba(105,120,225,0.29)",
      mid: "rgba(22,28,75,0.13)",
      dust: "rgba(3,4,14,0.78)",
    },
  };
  return table[key] || table.violet;
}

/** 液态星海图集：多条斜穿银河带 + 带外极稀疏宇宙点缀 */
function makeCosmicSeaTexture() {
  const S = 1024;
  const c = document.createElement("canvas");
  c.width = c.height = S;
  const ctx = c.getContext("2d");
  const rand = seaTextureRand(0xd4e88210);
  const bandDefs = [
    { angle: -0.42, half: 0.105, pal: "violet", spread: 1.05, stars: 5200, cx: 0.5, cy: 0.5 },
    { angle: -0.3, half: 0.088, pal: "cyan", spread: 0.9, stars: 4000, cx: 0.52, cy: 0.48 },
    { angle: -0.54, half: 0.082, pal: "rose", spread: 0.86, stars: 3600, cx: 0.48, cy: 0.52 },
    { angle: -0.36, half: 0.075, pal: "magenta", spread: 0.82, stars: 3200, cx: 0.51, cy: 0.51 },
    { angle: -0.48, half: 0.072, pal: "indigo", spread: 0.8, stars: 3000, cx: 0.49, cy: 0.49 },
  ];
  ctx.fillStyle = "#01030a";
  ctx.fillRect(0, 0, S, S);
  for (const b of bandDefs) {
    paintMilkyWayBand(ctx, S, rand, cosmicPaletteByKey(b.pal), {
      angle: b.angle,
      cx: b.cx,
      cy: b.cy,
      spread: b.spread,
      stars: b.stars,
    });
  }
  const bands = bandDefs.map((b) => ({ angle: b.angle, half: b.half, weight: 0.62 }));
  paintMilkyStarOcean(ctx, S, 6800, rand, bands);
  const mainAngle = bandDefs[0].angle;
  const mainHalf = bandDefs[0].half;

  const ca0 = Math.cos(mainAngle);
  const sa0 = Math.sin(mainAngle);
  for (let ci = 0; ci < 10; ci++) {
    const pal = cosmicPaletteByKey(["magenta", "cyan", "rose", "indigo", "violet"][ci % 5]);
    const along = ((ci / 9) * 2 - 1) * S * 0.62 + (rand() - 0.5) * S * 0.08;
    const across = (rand() - 0.5) * S * mainHalf * 1.1;
    const px = S * 0.5 + along * ca0 - across * sa0;
    const py = S * 0.5 + along * sa0 + across * ca0;
    ctx.globalCompositeOperation = "lighter";
    const g = ctx.createRadialGradient(px, py, 0, px, py, 28 + rand() * 40);
    g.addColorStop(0, pal.core);
    g.addColorStop(0.55, pal.mid);
    g.addColorStop(1, "transparent");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.ellipse(px, py, 22 + rand() * 36, 8 + rand() * 14, mainAngle + (rand() - 0.5) * 0.3, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalCompositeOperation = "source-over";
  }

  function inMainRiver(x, y, min = 0.1) {
    let w = 0;
    for (const b of bandDefs) {
      w = Math.max(w, milkyBandFactor(x, y, S, b.angle, S * b.half));
    }
    return w > min;
  }
  function allowSparseAccent(x, y) {
    return inMainRiver(x, y, 0.06) || rand() < 0.1;
  }

  ctx.globalCompositeOperation = "lighter";
  for (let i = 0; i < 14; i++) {
    const along = (rand() - 0.5) * S * 1.35;
    const ca = Math.cos(mainAngle);
    const sa = Math.sin(mainAngle);
    const cx = S * 0.5 + along * ca;
    const cy = S * 0.5 + along * sa;
    const across = (rand() - 0.5) * S * mainHalf * 1.2;
    const x = cx - across * sa;
    const y = cy + across * ca;
    ctx.strokeStyle = `rgba(255,${140 + ((rand() * 50) | 0)},${50 + ((rand() * 30) | 0)},${0.08 + rand() * 0.1})`;
    ctx.lineWidth = 0.6 + rand() * 1.2;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + ca * (18 + rand() * 32), y + sa * (18 + rand() * 32));
    ctx.stroke();
  }
  ctx.globalCompositeOperation = "source-over";
  const nebulaStopsList = [
    [
      [0, "rgba(80,120,210,0.045)"],
      [0.45, "rgba(30,50,110,0.022)"],
      [1, "transparent"],
    ],
    [
      [0, "rgba(120,80,200,0.04)"],
      [0.42, "rgba(40,30,90,0.02)"],
      [1, "transparent"],
    ],
  ];
  for (let i = 0; i < 6; i++) {
    const x = rand() * S;
    const y = rand() * S;
    if (!allowSparseAccent(x, y)) continue;
    const stops = nebulaStopsList[(rand() * nebulaStopsList.length) | 0];
    paintNebulaWisp(ctx, x, y, 12 + rand() * 22, 0.32 + rand() * 0.18, stops, rand);
  }
  for (let i = 0; i < 7; i++) {
    const x = rand() * S;
    const y = rand() * S;
    if (!inMainRiver(x, y, 0.14) && rand() > 0.12) continue;
    paintCosmicFilament(ctx, x, y, x + (rand() - 0.5) * 80, y + (rand() - 0.5) * 80, rand);
  }
  for (const b of bandDefs) {
    const cab = Math.cos(b.angle);
    const sab = Math.sin(b.angle);
    const clusterPal = cosmicPaletteByKey(b.pal);
    for (let k = 0; k < 8; k++) {
      const along = ((k / 5) * 2 - 1) * S * 0.58 + (rand() - 0.5) * S * 0.1;
      const across = (rand() - 0.5) * S * b.half * 1.35;
      const cx = b.cx * S + along * cab - across * sab;
      const cy = b.cy * S + along * sab + across * cab;
      paintCosmicGalaxyCluster(ctx, cx, cy, clusterPal, rand);
    }
  }
  for (let i = 0; i < 8; i++) {
    const along = (rand() - 0.5) * S * 1.28;
    const across = (rand() - 0.5) * S * mainHalf * 1.55;
    const cx = S * 0.5 + along * ca0 - across * sa0;
    const cy = S * 0.5 + along * sa0 + across * ca0;
    if (!inMainRiver(cx, cy, 0.05) && rand() > 0.06) continue;
    paintCosmicGalaxyCluster(ctx, cx, cy, cosmicPaletteByKey(pickCosmicPalette(rand)), rand);
  }
  for (let i = 0; i < 5; i++) {
    const x = rand() * S;
    const y = rand() * S;
    if (inMainRiver(x, y, 0.12) || rand() > 0.1) continue;
    paintCosmicGalaxyCluster(ctx, x, y, cosmicPaletteByKey(pickCosmicPalette(rand)), rand);
  }
  for (let i = 0; i < 36; i++) {
    const x = rand() * S;
    const y = rand() * S;
    if (!inMainRiver(x, y, 0.06) && rand() > 0.25) continue;
    paintStarCluster(ctx, x, y, rand);
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.minFilter = THREE.LinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function makeNebulaTex(hue) {
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
  if (hue === "pink") {
    g.addColorStop(0, "rgba(255,120,180,0.55)");
    g.addColorStop(0.45, "rgba(160,40,120,0.2)");
    g.addColorStop(1, "transparent");
  } else if (hue === "cyan") {
    g.addColorStop(0, "rgba(80,180,255,0.45)");
    g.addColorStop(0.5, "rgba(40,80,160,0.12)");
    g.addColorStop(1, "transparent");
  } else {
    g.addColorStop(0, "rgba(180,80,255,0.4)");
    g.addColorStop(1, "transparent");
  }
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 256, 256);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function buildAuthSatellite() {
  const sat = new THREE.Group();
  sat.name = "auth-satellite";
  const bodyMat = new THREE.MeshStandardMaterial({
    color: 0xe2e8f8,
    metalness: 0.78,
    roughness: 0.22,
    emissive: 0x3a5588,
    emissiveIntensity: 0.65,
  });
  const panelMat = new THREE.MeshStandardMaterial({
    color: 0x2868aa,
    metalness: 0.45,
    roughness: 0.28,
    emissive: 0x22a8ff,
    emissiveIntensity: 1.05,
  });
  const goldMat = new THREE.MeshStandardMaterial({
    color: 0xffd080,
    metalness: 0.88,
    roughness: 0.25,
    emissive: 0x886622,
    emissiveIntensity: 0.55,
  });
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.42, 0.32), bodyMat);
  const panelL = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.06, 0.55), panelMat);
  panelL.position.x = -0.62;
  const panelR = panelL.clone();
  panelR.position.x = 0.62;
  const dish = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.12, 0.06, 16), goldMat);
  dish.rotation.x = Math.PI / 2;
  dish.position.set(0, 0.26, 0.14);
  const antenna = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, 0.55, 8), goldMat);
  antenna.position.set(0.08, 0.48, 0);
  const led = new THREE.Mesh(
    new THREE.SphereGeometry(0.07, 10, 10),
    new THREE.MeshBasicMaterial({ color: 0x66eeff })
  );
  led.position.set(0.14, 0.16, 0.2);
  sat.add(body, panelL, panelR, dish, antenna, led);
  const satLight = new THREE.PointLight(0x99ccff, 0.85, 18);
  satLight.position.set(0, 0.2, 0.5);
  sat.add(satLight);
  const halo = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: makeNebulaTex("violet"),
      color: 0xa8d0ff,
      transparent: true,
      opacity: 0.42,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    })
  );
  halo.scale.set(14, 14, 1);
  halo.position.set(0, 0, -0.4);
  sat.add(halo);
  const haloTight = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: makeNebulaTex("pink"),
      color: 0x88eeff,
      transparent: true,
      opacity: 0.55,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    })
  );
  haloTight.scale.set(6.5, 6.5, 1);
  haloTight.position.set(0.1, 0.05, 0.2);
  sat.add(haloTight);
  sat.position.set(-9.5, 12.8, -21.5);
  sat.scale.setScalar(2.65);
  return {
    root: sat,
    anchor: { x: -9.5, y: 12.8, z: -21.5 },
    phase: 1.85,
    halo,
    haloTight,
    satLight,
    led,
  };
}

function buildFallbackAstronaut() {
  const g = new THREE.Group();
  g.name = "astro-fallback";
  const suitMat = new THREE.MeshStandardMaterial({
    color: 0xd8dce8,
    metalness: 0.55,
    roughness: 0.38,
  });
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.32, 0.72, 12, 24), suitMat);
  body.position.y = 0.35;
  const helmet = new THREE.Mesh(
    new THREE.SphereGeometry(0.34, 32, 32),
    new THREE.MeshStandardMaterial({
      color: 0x1a1420,
      metalness: 0.9,
      roughness: 0.12,
      envMapIntensity: 1.2,
      emissive: 0x331822,
      emissiveIntensity: 0.25,
    })
  );
  helmet.position.y = 1.05;
  helmet.scale.set(1.05, 1.05, 1.05);
  const visor = new THREE.Mesh(
    new THREE.SphereGeometry(0.28, 32, 32, 0, Math.PI * 2, 0, Math.PI * 0.42),
    new THREE.MeshStandardMaterial({
      color: 0x883355,
      metalness: 0.95,
      roughness: 0.05,
      emissive: 0x552244,
      emissiveIntensity: 0.35,
      side: THREE.DoubleSide,
    })
  );
  visor.position.set(0, 1.06, 0.12);
  visor.rotation.x = 0.35;
  g.add(body, helmet, visor);
  return g;
}

const root = document.querySelector(".auth-bg");
const canvas = document.getElementById("auth-bg-canvas");
if (root && canvas) {
  try {
    const cursorEl = document.getElementById("auth-bg-cursor");
    const prefersReduced =
      window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let w = window.innerWidth;
    let h = window.innerHeight;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x04020c);
    scene.fog = new THREE.Fog(0x140818, 18, 95);

    const camera = new THREE.PerspectiveCamera(46, w / h, 0.1, 200);
    camera.position.set(0, 7.05, 15.4);
    /** 半俯瞰：画面约 60% 海面 / 40% 上方星空 */
    const CAM_BASE_Y = 7.05;
    const CAM_BASE_Z = 15.4;
    const CAM_LOOK_Y = 2.35;
    const CAM_LOOK_Z = -17.2;

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.35));
    renderer.setSize(w, h, false);
    renderer.setClearColor(0x020108, 1);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.68;
    renderer.localClippingEnabled = false;

    let composer = null;
    let useComposer = true;
    try {
      composer = new EffectComposer(renderer);
      composer.addPass(new RenderPass(scene, camera));
      composer.addPass(new UnrealBloomPass(new THREE.Vector2(w, h), 0.038, 0.34, 0.88));
    } catch {
      useComposer = false;
    }

    // —— 远景星空 ——
    const skyGroup = new THREE.Group();
    skyGroup.position.set(0, 7.2, -42);
    scene.add(skyGroup);
    const starGeo = new THREE.BufferGeometry();
    const sc = 1100;
    const starPos = new Float32Array(sc * 3);
    const starCol = new Float32Array(sc * 3);
    for (let i = 0; i < sc; i++) {
      starPos[i * 3] = (Math.random() - 0.5) * 140;
      starPos[i * 3 + 1] = Math.random() * 62 - 3;
      starPos[i * 3 + 2] = -Math.random() * 35;
      const b = 0.35 + Math.random() * 0.45;
      starCol[i * 3] = b;
      starCol[i * 3 + 1] = b * (0.85 + Math.random() * 0.15);
      starCol[i * 3 + 2] = b * (0.9 + Math.random() * 0.2);
    }
    starGeo.setAttribute("position", new THREE.BufferAttribute(starPos, 3));
    starGeo.setAttribute("color", new THREE.BufferAttribute(starCol, 3));
    skyGroup.add(
      new THREE.Points(
        starGeo,
        new THREE.PointsMaterial({
          size: 0.22,
          sizeAttenuation: true,
          vertexColors: true,
          transparent: true,
          opacity: 0.65,
          depthWrite: false,
        })
      )
    );
    [
      { hue: "violet", x: -26, y: 16, s: 34 },
      { hue: "pink", x: 22, y: 12, s: 28 },
    ].forEach((n) => {
      const sp = new THREE.Sprite(
        new THREE.SpriteMaterial({
          map: makeNebulaTex(n.hue),
          transparent: true,
          opacity: 0.14,
          depthWrite: false,
          blending: THREE.AdditiveBlending,
        })
      );
      sp.position.set(n.x, n.y, -12);
      sp.scale.set(n.s, n.s * 0.55, 1);
      skyGroup.add(sp);
    });
    const auroraRoot = new THREE.Group();
    auroraRoot.position.set(0, 17.5, -30);
    scene.add(auroraRoot);
    const auroraUniforms = { uTime: { value: 0 }, uPhase: { value: 0 } };
    const auroraMat = () =>
      new THREE.ShaderMaterial({
        uniforms: auroraUniforms,
        vertexShader: auroraVert,
        fragmentShader: auroraFrag,
        transparent: true,
        depthWrite: false,
        depthTest: true,
        blending: THREE.AdditiveBlending,
        side: THREE.DoubleSide,
      });
    const auroraMain = new THREE.Mesh(new THREE.PlaneGeometry(158, 52, 1, 1), auroraMat());
    auroraMain.position.set(0, 0, 0);
    auroraMain.rotation.x = -0.12;
    auroraMain.renderOrder = -2;
    auroraRoot.add(auroraMain);
    const auroraSide = new THREE.Mesh(new THREE.PlaneGeometry(88, 30, 1, 1), auroraMat());
    auroraSide.position.set(-32, 4, 2);
    auroraSide.rotation.set(-0.1, 0.22, 0);
    auroraSide.renderOrder = -2;
    auroraRoot.add(auroraSide);
    const authSatellite = buildAuthSatellite();
    scene.add(authSatellite.root);
    authSatellite.root.renderOrder = 4;
    // —— 液态银河海面 ——
    const cosmicSeaTex = makeCosmicSeaTexture();
    const RIPPLE_SLOTS = 6;
    const HOVER_RIPPLE_SLOT = 0;
    const ripples = Array.from({ length: RIPPLE_SLOTS }, () => new THREE.Vector4(0, 0, -1e4, 0));
    const seaUniforms = {
      uTime: { value: 0 },
      uCamera: { value: new THREE.Vector3() },
      uCosmicTex: { value: cosmicSeaTex },
      uRipples: { value: ripples },
    };
    const seaRaycaster = new THREE.Raycaster();
    const seaNdc = new THREE.Vector2();
    const seaMesh = new THREE.Mesh(
      new THREE.PlaneGeometry(160, 90, 148, 88),
      new THREE.ShaderMaterial({
        uniforms: seaUniforms,
        vertexShader: seaVert,
        fragmentShader: seaFrag,
        side: THREE.FrontSide,
      })
    );
    seaMesh.rotation.x = -Math.PI / 2;
    seaMesh.position.y = 0;
    seaMesh.renderOrder = 0;
    scene.add(seaMesh);

    scene.add(new THREE.HemisphereLight(0x4a88bb, 0x03080f, 0.5));
    const sun = new THREE.DirectionalLight(0xdd55aa, 0.48);
    sun.position.set(-6, 12, 8);
    scene.add(sun);
    const fill = new THREE.DirectionalLight(0x4488cc, 0.28);
    fill.position.set(8, 6, 10);
    scene.add(fill);

    function createSkyAstronaut(cfg) {
      const astroRoot = new THREE.Group();
      astroRoot.position.set(cfg.x, cfg.y, cfg.z);
      scene.add(astroRoot);

      const astroFront = new THREE.PointLight(0xfff0f8, 0.4, 14);
      astroFront.position.set(0, 1.1, 1.4);
      astroRoot.add(astroFront);

      const astroModel = new THREE.Group();
      astroModel.name = "astro-model";
      astroRoot.add(astroModel);
      astroModel.add(buildFallbackAstronaut());

      const drift = {
        tx: cfg.x,
        ty: cfg.y,
        tz: cfg.z,
        nextRetarget: 0,
        side: cfg.side,
        phase: cfg.phase,
        zone: cfg.zone || "center",
      };

      return { root: astroRoot, model: astroModel, drift };
    }

    const astroVis = new THREE.Vector3();
    const ASTRO_NDC_BOX = { xMin: -0.72, xMax: 0.72, yMin: -0.08, yMax: 0.72 };
    const ASTRO_WORLD = { xMin: -11.5, xMax: 11.5, yMin: 5.4, yMax: 14.2, zMin: -19.2, zMax: -12.2 };
    const ASTRO_ZONES = {
      left: { xMin: -11.5, xMax: -3.6 },
      center: { xMin: -3.4, xMax: 3.4 },
      right: { xMin: 3.6, xMax: 11.5 },
    };

    function astroZoneX(drift) {
      return ASTRO_ZONES[drift.zone] || ASTRO_ZONES.center;
    }

    function clampAstroDrift(drift) {
      const zx = astroZoneX(drift);
      drift.tx = THREE.MathUtils.clamp(drift.tx, zx.xMin, zx.xMax);
      drift.ty = THREE.MathUtils.clamp(drift.ty, ASTRO_WORLD.yMin, ASTRO_WORLD.yMax);
      drift.tz = THREE.MathUtils.clamp(drift.tz, ASTRO_WORLD.zMin, ASTRO_WORLD.zMax);
    }

    function clampAstroRootPos(drift, pos) {
      const zx = astroZoneX(drift);
      pos.x = THREE.MathUtils.clamp(pos.x, zx.xMin, zx.xMax);
      pos.y = THREE.MathUtils.clamp(pos.y, ASTRO_WORLD.yMin, ASTRO_WORLD.yMax);
      pos.z = THREE.MathUtils.clamp(pos.z, ASTRO_WORLD.zMin, ASTRO_WORLD.zMax);
    }

    function constrainAstroOnScreen(astroRoot, drift, cam) {
      astroVis.copy(astroRoot.position);
      astroVis.project(cam);
      const ox = astroVis.x;
      const oy = astroVis.y;
      const cx = THREE.MathUtils.clamp(ox, ASTRO_NDC_BOX.xMin, ASTRO_NDC_BOX.xMax);
      const cy = THREE.MathUtils.clamp(oy, ASTRO_NDC_BOX.yMin, ASTRO_NDC_BOX.yMax);
      const dx = ox - cx;
      const dy = oy - cy;
      if (Math.abs(dx) < 0.004 && Math.abs(dy) < 0.004) return;
      astroRoot.position.x -= dx * 3.4;
      astroRoot.position.y -= dy * 4.8;
      clampAstroDrift(drift);
      clampAstroRootPos(drift, astroRoot.position);
      drift.tx = THREE.MathUtils.lerp(drift.tx, astroRoot.position.x, 0.35);
      drift.ty = THREE.MathUtils.lerp(drift.ty, astroRoot.position.y, 0.35);
      drift.tz = THREE.MathUtils.lerp(drift.tz, astroRoot.position.z, 0.25);
    }

    const astronauts = [
      createSkyAstronaut({ x: -8.2, y: 11.2, z: -16.5, side: -1, phase: 0, zone: "left" }),
      createSkyAstronaut({ x: 0.4, y: 9.4, z: -15.8, side: 0, phase: 2.4, zone: "center" }),
      createSkyAstronaut({ x: 8.5, y: 10.6, z: -17.2, side: 1, phase: 4.1, zone: "right" }),
    ];
    root.classList.add("auth-bg-ready");

    function pickAstroSkyTarget(drift, t) {
      const zx = astroZoneX(drift);
      const wy = ASTRO_WORLD.yMax - ASTRO_WORLD.yMin;
      const wz = ASTRO_WORLD.zMax - ASTRO_WORLD.zMin;
      drift.tx = zx.xMin + Math.random() * (zx.xMax - zx.xMin);
      drift.ty = ASTRO_WORLD.yMin + Math.random() * wy;
      drift.tz = ASTRO_WORLD.zMin + Math.random() * wz;
      clampAstroDrift(drift);
      drift.nextRetarget = t + 3.5 + Math.random() * 5.5;
    }
    astronauts.forEach((a) => {
      a.drift.tx = a.root.position.x;
      a.drift.ty = a.root.position.y;
      a.drift.tz = a.root.position.z;
      pickAstroSkyTarget(a.drift, 0);
    });

    function prepareAstroMesh(object) {
      object.traverse((child) => {
        if (child.isMesh && child.material) {
          const mats = Array.isArray(child.material) ? child.material : [child.material];
          mats.forEach((m) => {
            if (m.map) m.map.colorSpace = THREE.SRGBColorSpace;
            m.metalness = Math.min(0.72, (m.metalness ?? 0.3) + 0.25);
            m.roughness = Math.max(0.22, (m.roughness ?? 0.5) - 0.18);
            m.envMapIntensity = 0.85;
            m.clippingPlanes = null;
            m.clipShadows = false;
            if (m.color) {
              const hsl = {};
              m.color.getHSL(hsl);
              if (hsl.l > 0.5 && hsl.s < 0.35) {
                m.color.multiplyScalar(1.08);
              }
              if (hsl.l > 0.35 && hsl.s < 0.5) {
                m.emissive = new THREE.Color(0x442233);
                m.emissiveIntensity = 0.22;
              }
            }
          });
        }
      });
      const box = new THREE.Box3().setFromObject(object);
      const maxDim = Math.max(...box.getSize(new THREE.Vector3()).toArray(), 0.001);
      object.scale.setScalar(1.45 / maxDim);
      box.setFromObject(object);
      object.position.sub(box.getCenter(new THREE.Vector3()));
      object.rotation.y = 0;
      return object;
    }

    function mountAstronauts(gltfScene) {
      astronauts.forEach((a, i) => {
        const fb = a.model.getObjectByName("astro-fallback");
        if (fb) a.model.remove(fb);
        const src = i === 0 ? gltfScene : cloneSkinned(gltfScene);
        a.model.add(prepareAstroMesh(src));
      });
      root.classList.add("auth-bg-ready");
    }

    new GLTFLoader().load(MODEL_CANDIDATES[0], (g) => mountAstronauts(g.scene), undefined, () => {
      new GLTFLoader().load(MODEL_CANDIDATES[1], (g) => mountAstronauts(g.scene), undefined, () => {
        new GLTFLoader().load(MODEL_CANDIDATES[2], (g) => mountAstronauts(g.scene));
      });
    });

    const mouse = { x: 0.5, y: 0.5, tx: 0.5, ty: 0.5 };
    const hoverSea = { x: 0, z: 0, tx: 0, tz: 0, str: 0, on: false };
    let seaHoverGlow = 0;
    const clock = new THREE.Clock();
    let raf = 0;

    function seaPointFromClient(clientX, clientY) {
      seaNdc.x = (clientX / Math.max(w, 1)) * 2 - 1;
      seaNdc.y = -(clientY / Math.max(h, 1)) * 2 + 1;
      seaRaycaster.setFromCamera(seaNdc, camera);
      const hits = seaRaycaster.intersectObject(seaMesh);
      return hits.length ? hits[0].point : null;
    }

    function setSeaRipple(x, z, strength, slot) {
      const t = seaUniforms.uTime.value;
      ripples[slot].set(x, z, t, strength);
    }

    function pickFreeRippleSlot() {
      const t = seaUniforms.uTime.value;
      let slot = 1;
      for (let i = 1; i < RIPPLE_SLOTS; i++) {
        if (ripples[i].w < 0.02) return i;
        const age = t - ripples[i].z;
        if (age > 4.8) slot = i;
      }
      return slot;
    }

    function spawnSeaRippleAt(x, z, strength) {
      setSeaRipple(x, z, strength, pickFreeRippleSlot());
    }

    function spawnClickRipple(clientX, clientY) {
      const p = seaPointFromClient(clientX, clientY);
      if (!p) return;
      spawnSeaRippleAt(p.x, p.z, 0.9);
      const dom = document.createElement("div");
      dom.className = "auth-bg-ripple";
      dom.style.left = `${clientX}px`;
      dom.style.top = `${clientY}px`;
      root.appendChild(dom);
      dom.addEventListener("animationend", () => dom.remove(), { once: true });
    }

    function onResize() {
      w = window.innerWidth;
      h = window.innerHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h, false);
      if (useComposer && composer) composer.setSize(w, h);
    }

    function tick() {
      const time = performance.now() * 0.001 * TIME_SCALE;
      mouse.x += (mouse.tx - mouse.x) * 0.06;
      mouse.y += (mouse.ty - mouse.y) * 0.06;

      camera.position.x = (mouse.x - 0.5) * 1.28;
      camera.position.y = CAM_BASE_Y + (mouse.y - 0.5) * 0.92;
      camera.position.z = CAM_BASE_Z + (mouse.y - 0.5) * 1.38;
      const astroMidX =
        astronauts.reduce((s, a) => s + a.root.position.x, 0) / astronauts.length;
      const astroMidY =
        astronauts.reduce((s, a) => s + a.root.position.y, 0) / astronauts.length;
      const gazeX = (mouse.x - 0.5) * 3.4 + astroMidX * 0.06;
      const gazeY =
        CAM_LOOK_Y + (mouse.y - 0.5) * 0.46 + Math.max(0, astroMidY - 8) * 0.04;
      camera.lookAt(gazeX, gazeY, CAM_LOOK_Z);

      seaUniforms.uTime.value = prefersReduced ? 0 : time;
      auroraUniforms.uTime.value = prefersReduced ? 0 : time;
      seaUniforms.uCamera.value.copy(camera.position);
      if (!prefersReduced) {
        for (let i = 1; i < RIPPLE_SLOTS; i++) {
          const age = time - ripples[i].z;
          if (ripples[i].w > 0.001 && age > 6.8) ripples[i].w = 0;
        }
        const hRip = ripples[HOVER_RIPPLE_SLOT];
        if (hoverSea.on) {
          hoverSea.x += (hoverSea.tx - hoverSea.x) * 0.16;
          hoverSea.z += (hoverSea.tz - hoverSea.z) * 0.16;
          hoverSea.str += (0.36 - hoverSea.str) * 0.05;
          if (hRip.w < 0.02) hRip.z = time;
          hRip.x = hoverSea.x;
          hRip.y = hoverSea.z;
          hRip.w = hoverSea.str;
          seaHoverGlow += (1 - seaHoverGlow) * 0.06;
        } else {
          hoverSea.str += (0 - hoverSea.str) * 0.07;
          if (hoverSea.str < 0.012) {
            hRip.w = 0;
            hoverSea.str = 0;
          } else {
            hRip.x += (hoverSea.tx - hRip.x) * 0.12;
            hRip.y += (hoverSea.tz - hRip.y) * 0.12;
            hRip.w = hoverSea.str;
          }
          seaHoverGlow += (0 - seaHoverGlow) * 0.08;
        }
        root.style.setProperty("--auth-sea-hover", seaHoverGlow.toFixed(3));
      }
      const drift = prefersReduced ? 0 : time;
      cosmicSeaTex.offset.x = drift * 0.011;
      cosmicSeaTex.offset.y = drift * 0.0055;

      if (!prefersReduced) {
        const satPh = authSatellite.phase;
        const satA = authSatellite.anchor;
        authSatellite.root.position.x =
          satA.x + Math.sin(time * 0.2 + satPh) * 3.2 + Math.cos(time * 0.13 + 0.5) * 1.4;
        authSatellite.root.position.y =
          satA.y + Math.sin(time * 0.17 + satPh * 0.6) * 1.6;
        authSatellite.root.position.z =
          satA.z + Math.sin(time * 0.11 + satPh) * 1.1;
        authSatellite.root.rotation.y = time * 0.06 + satPh;
        authSatellite.root.rotation.x = -0.12 + Math.sin(time * 0.19) * 0.07;
        authSatellite.root.rotation.z = Math.sin(time * 0.31 + satPh) * 0.09;
        const satPulse = Math.sin(time * 1.35 + satPh) * 0.5 + 0.5;
        authSatellite.halo.material.opacity = 0.32 + satPulse * 0.22;
        authSatellite.haloTight.material.opacity = 0.42 + satPulse * 0.28;
        authSatellite.satLight.intensity = 0.72 + satPulse * 0.38;
        authSatellite.led.material.color.setHSL(0.52, 0.85, 0.55 + satPulse * 0.35);
        const driftK = 0.014;
        astronauts.forEach((a) => {
          a.model.renderOrder = 3;
          const { drift, root: astroRoot } = a;
          const ph = drift.phase;
          if (time >= drift.nextRetarget) pickAstroSkyTarget(drift, time);
          astroRoot.position.x += (drift.tx - astroRoot.position.x) * driftK;
          astroRoot.position.y += (drift.ty - astroRoot.position.y) * driftK;
          astroRoot.position.z += (drift.tz - astroRoot.position.z) * driftK;
          astroRoot.position.x += Math.sin(time * 0.62 + ph) * 0.028;
          astroRoot.position.y += Math.sin(time * 0.48 + 1.2 + ph) * 0.022;
          clampAstroDrift(drift);
          clampAstroRootPos(drift, astroRoot.position);
          constrainAstroOnScreen(astroRoot, drift, camera);
          const spin =
            drift.zone === "right" ? 1 : drift.zone === "left" ? -1 : drift.phase > 3 ? 1 : -1;
          astroRoot.rotation.y += 0.0036 * spin;
          astroRoot.rotation.z = Math.sin(time * 0.38 + ph) * 0.1;
          astroRoot.rotation.x = Math.sin(time * 0.31 + 0.8 + ph) * 0.07;
        });
      }

      if (useComposer && composer) composer.render();
      else renderer.render(scene, camera);
    }

    function loop() {
      tick();
      raf = requestAnimationFrame(loop);
    }

    window.addEventListener("resize", onResize);
    window.addEventListener(
      "pointermove",
      (e) => {
        mouse.tx = e.clientX / Math.max(window.innerWidth, 1);
        mouse.ty = e.clientY / Math.max(window.innerHeight, 1);
        root.classList.add("is-pointer-active");
        if (cursorEl) {
          cursorEl.style.transform = `translate(${e.clientX}px, ${e.clientY}px) translate(-50%, -50%)`;
        }
        if (!prefersReduced) {
          const p = seaPointFromClient(e.clientX, e.clientY);
          if (p) {
            hoverSea.tx = p.x;
            hoverSea.tz = p.z;
            hoverSea.on = true;
            root.classList.add("auth-bg-ripple-sea");
          } else {
            hoverSea.on = false;
            root.classList.remove("auth-bg-ripple-sea");
          }
        }
      },
      { passive: true }
    );

    window.addEventListener(
      "pointerdown",
      (e) => {
        if (prefersReduced) return;
        if (e.target.closest(".auth-card")) return;
        spawnClickRipple(e.clientX, e.clientY);
      },
      { passive: true }
    );

    onResize();
    root.classList.add("auth-bg-webgl");
    loop();

    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        cancelAnimationFrame(raf);
        raf = 0;
      } else if (!raf) {
        clock.getDelta();
        loop();
      }
    });
  } catch (err) {
    console.error("[auth-bg]", err);
    window.__authBgFallback?.(err?.message || "init");
  }
}