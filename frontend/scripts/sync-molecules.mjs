// Run manually: node frontend/scripts/sync-molecules.mjs
// PubChem is only contacted during this refresh, never when a shopper opens a card.
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const references = [
  ["苯", "Benzene", "芳香环", "六个碳原子围成一个环，是这件作品六角轮廓的结构参考。"],
  ["尼古丁", "Nicotine", "双环骨架", "两个不同的含氮环通过单键相连，形成有转折的轮廓。"],
  ["血清素", "Serotonin", "稠合双环", "稠合的环系与一条短侧链，构成作品中闭合与延伸的线条。"],
  ["肾上腺素", "Epinephrine", "芳环与侧链", "环上的取代基和伸出的侧链，让结构拥有不同方向的分支。"],
  ["咖啡因", "Caffeine", "含氮双环", "相互连接的含氮环系，带来紧凑而有层次的几何轮廓。"],
  ["可卡因", "Cocaine", "多环骨架", "桥环与芳香环形成复杂骨架，卡片用于观察其连接方式。"],
  ["LSD", "Lysergic acid diethylamide", "多环骨架", "多个相连的环与侧链，提供了适合观察的结构层次。"],
  ["吗啡", "Morphine", "稠合多环", "多环相连的骨架，展示了如何将立体连接转译为平面线条。"],
  ["地巴唑", "Bendazol", "双环与芳环", "含氮环系与另一芳香环通过连接基团相接，形成疏密对比。"],
  ["戊巴比妥", "Pentobarbital", "环与分支", "环状核心连接不同的碳链分支，构成有节奏的线条。"],
  ["薄荷醇", "Levomenthol", "六元环", "以常见的左旋薄荷醇为结构参考；商品名称本身未限定立体异构体。"],
  ["乙醇", "Ethanol", "短链结构", "两个碳原子与羟基构成简洁的链状骨架。"],
  ["裸盖菇素", "Psilocybin", "稠环与分支", "稠合环系、侧链与含磷基团，带来不同尺度的结构细节。"],
];
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function get(path, binary = false) {
  for (let attempt = 0; attempt < 3; attempt++) {
    await sleep(350);
    try {
      const response = await fetch(`https://pubchem.ncbi.nlm.nih.gov/rest/pug/${path}`, { signal: AbortSignal.timeout(20000) });
      if (!response.ok) throw new Error(`PubChem HTTP ${response.status}`);
      return binary ? Buffer.from(await response.arrayBuffer()) : response.json();
    } catch (error) {
      if (attempt === 2) throw error;
      await sleep(1500);
    }
  }
}

await mkdir(`${root}public/images/molecules`, { recursive: true });
await mkdir(`${root}app/data`, { recursive: true });
const records = {};
for (const [name, referenceName, family, description] of references) {
  const result = await get(`compound/name/${encodeURIComponent(referenceName)}/property/MolecularFormula,MolecularWeight,IUPACName/JSON`);
  const properties = result.PropertyTable?.Properties;
  if (properties?.length !== 1) throw new Error(`Ambiguous molecule: ${name}`);
  const p = properties[0];
  if (!p.CID || !p.MolecularFormula || !p.MolecularWeight || !p.IUPACName) throw new Error(`Incomplete molecule: ${name}`);
  const png = await get(`compound/cid/${p.CID}/PNG?image_size=large`, true);
  if (png.subarray(0, 8).toString("hex") !== "89504e470d0a1a0a") throw new Error(`Invalid structure image: ${name}`);
  await writeFile(`${root}public/images/molecules/${p.CID}.png`, png);
  records[name] = {
    cid: p.CID, referenceName, family, description,
    formula: p.MolecularFormula, molecularWeight: p.MolecularWeight, iupacName: p.IUPACName,
    image: `/images/molecules/${p.CID}.png`, sourceUrl: `https://pubchem.ncbi.nlm.nih.gov/compound/${p.CID}`,
  };
  console.log(`${name}: CID ${p.CID}`);
}
// Replace the snapshot only after every reference has passed validation.
await writeFile(`${root}app/data/molecules.json`, JSON.stringify({
  source: "PubChem / NIH", retrievedAt: new Date().toISOString().slice(0, 10), molecules: records,
}, null, 2) + "\n");
console.log(`Saved ${Object.keys(records).length} verified molecular references.`);
