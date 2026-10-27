import { Atom, ExternalLink } from "lucide-react";
import Image from "next/image";
import snapshot from "../data/molecules.json";

type Molecule = {
  cid: number; referenceName: string; family: string; description: string;
  formula: string; molecularWeight: string; iupacName: string; image: string; sourceUrl: string;
};
const molecules: Record<string, Molecule> = snapshot.molecules;
const ambiguousNames: Record<string, string> = {
  "海洛因I型": "“I型”是作品系列名称，尚未指定可唯一对应的化学结构。",
  "海洛因II型": "“II型”是作品系列名称，尚未指定可唯一对应的化学结构。",
  "THC": "THC 存在不同异构体，需确认作品参考的具体结构。",
  "迷幻剂": "这是一个类别名称，不能对应唯一的分子式或结构。",
};

export default function MoleculeCard({ productName }: { productName: string }) {
  const molecule = molecules[productName];
  if (!molecule) return <section className="molecule-card molecule-card-pending" aria-label="分子资料卡">
    <Atom size={30} aria-hidden="true" />
    <div><p className="eyebrow">MOLECULE NOTES</p><h2>分子资料卡 · 结构待确认</h2>
      <p>{ambiguousNames[productName] || "这件作品尚未关联经核对的分子资料。"}确认后再展示科学数据。</p>
    </div>
  </section>;

  return <section className="molecule-card" aria-label={`${productName}分子资料卡`}>
    <div className="molecule-structure">
      <Image src={molecule.image} alt={`${productName}的结构参考图（${molecule.referenceName}，PubChem CID ${molecule.cid}）`} width={360} height={280} loading="lazy" unoptimized />
      <span>二维结构参考图</span>
    </div>
    <div className="molecule-copy">
      <p className="eyebrow"><Atom size={15} aria-hidden="true" /> MOLECULE NOTES</p>
      <div className="molecule-heading"><h2>分子资料卡</h2><span className="molecule-family">{molecule.family}</span></div>
      <p className="molecule-english">{molecule.referenceName}</p>
      <p className="molecule-description">{molecule.description}</p>
      <dl className="molecule-facts">
        <div><dt>分子式</dt><dd>{molecule.formula.split(/(\d+)/).map((part, index) => /^\d+$/.test(part) ? <sub key={index}>{part}</sub> : <span key={index}>{part}</span>)}</dd></div>
        <div><dt>分子量</dt><dd>{molecule.molecularWeight} <small>g/mol</small></dd></div>
        <div><dt>PubChem CID</dt><dd>{molecule.cid}</dd></div>
      </dl>
      <details className="molecule-naming"><summary>查看系统命名</summary><p lang="en">{molecule.iupacName}</p></details>
      <div className="molecule-source"><span>来源：PubChem · 资料更新 {snapshot.retrievedAt}</span><a href={molecule.sourceUrl} target="_blank" rel="noopener noreferrer">查看原始资料 <ExternalLink size={13} aria-hidden="true" /></a></div>
      <p className="molecule-footnote">分子信息用于理解设计，不代表首饰的材质或功效。</p>
    </div>
  </section>;
}
