import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import sharp from "sharp";
import pngToIco from "png-to-ico";

const root = resolve(import.meta.dirname, "..");
const source = resolve(root, "assets", "app-icon.svg");
const pngTarget = resolve(root, "assets", "app-icon.png");
const icoTarget = resolve(root, "assets", "app-icon.ico");

await mkdir(dirname(pngTarget), { recursive: true });

const svgBuffer = await readFile(source);
const pngBuffer = await sharp(svgBuffer).resize(512, 512).png().toBuffer();
await writeFile(pngTarget, pngBuffer);

const iconSizes = [256, 128, 64, 48, 32, 16];
const icoSources = await Promise.all(
  iconSizes.map((size) => sharp(svgBuffer).resize(size, size).png().toBuffer()),
);
const icoBuffer = await pngToIco(icoSources);
await writeFile(icoTarget, icoBuffer);

console.log("generated app-icon.png and app-icon.ico");
