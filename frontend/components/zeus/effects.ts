// Random shapes for lightning and falling coins. They only decorate the screen: game results
// come from the backend. They run in lazy useState, so a shape stays the same between renders.

export function between(min: number, max: number) {
  return min + Math.random() * (max - min)
}

export function chance() {
  return Math.random() > 0.5
}

export function makeBolt() {
  let x = 500
  let path = 'M 500 0'
  for (let step = 1; step <= 10; step++) {
    x += between(-75, 75)
    path += ` L ${x} ${step * 100}`
  }

  return {
    path,
    branches: [0, 1, 2].map(
      (index) => `M ${between(400, 600)} ${100 + index * 200} L ${between(0, 1000)} ${between(0, 1000)}`,
    ),
  }
}

export function makeRandomBolts(count: number) {
  return Array.from({ length: count }, () => ({
    path: `M ${between(0, 1000)} 0 L ${between(0, 1000)} 250 L ${between(0, 1000)} 500 L ${between(0, 1000)} 750 L ${between(0, 1000)} 1000`,
    repeatDelay: between(0, 2),
  }))
}

export function makeRising(count: number) {
  return Array.from({ length: count }, () => ({
    scale: between(0.5, 1),
    x: between(0, 100),
    duration: between(1.5, 2.5),
    delay: between(0, 0.5),
  }))
}

export function makeSparks(count: number) {
  return Array.from({ length: count }, () => ({
    x: between(0, 100),
    y: between(0, 100),
    duration: between(0.8, 1.4),
    delay: between(0, 2),
    gold: chance(),
  }))
}

export function makeBigWinCoins(count: number) {
  return Array.from({ length: count }, () => ({
    size: between(16, 40),
    startX: between(0, 100),
    endX: between(0, 100),
    drift: between(-60, 60),
    rotate: between(360, 1080),
    duration: between(2, 4),
    delay: between(0, 2.5),
    front: chance(),
  }))
}

export function makeGoldRain(count: number) {
  return Array.from({ length: count }, () => ({
    x: between(0, 100),
    rotate: between(360, 720),
    duration: between(2.5, 5),
    delay: between(0, 4),
    round: chance(),
    gold: chance(),
  }))
}

export function makeJackpotCoins(count: number) {
  return Array.from({ length: count }, () => ({
    x: between(0, 100),
    width: between(18, 36),
    height: between(18, 36),
    rotate: between(0, 720),
    duration: between(1.5, 3.5),
    delay: between(0, 3),
  }))
}
