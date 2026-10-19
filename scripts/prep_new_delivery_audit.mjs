// Read only the explicitly supplied delivery; retain hashes and missing-MTL facts.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const project=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const root=String.raw`C:\Users\Senac\Downloads\NÃO APAGUE ESSA PASTA Sou Aluno Programador no GitHub, pois utilizo pra programar no GitHub e no VScode\Tudo pra colocar no jogo`;
const scopes=['ônibus','Parada de ônibus','Terminal de Ônibus','Personagens/Estudiante S. XVIII','Esqueleto/Raio X Anatomia Humana'];
const walk=d=>fs.readdirSync(d,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(d,e.name)):[path.join(d,e.name)]);
const sha=data=>crypto.createHash('sha256').update(data).digest('hex');
const records=[];
for(const scope of scopes){
  const files=walk(path.join(root,scope)),objs=[],glbs=[];
  for(const p of files){
    const ext=path.extname(p).toLowerCase();
    if(ext==='.obj'){
      const data=fs.readFileSync(p),text=data.toString('utf8');let verts=0,faces=0,tris=0,uvs=0;
      const min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity],libs=new Set(),materials=new Set(),geometry=[];
      for(const line of text.split(/\r?\n/)){
        if(line.startsWith('v ')){verts++;const v=line.trim().split(/\s+/).slice(1,4).map(Number);for(let i=0;i<3;i++){min[i]=Math.min(min[i],v[i]);max[i]=Math.max(max[i],v[i]);}}
        if(line.startsWith('f ')){faces++;tris+=line.trim().split(/\s+/).length-3;}
        if(line.startsWith('vt '))uvs++;
        if(line.startsWith('mtllib '))libs.add(line.slice(7));
        if(line.startsWith('usemtl '))materials.add(line.slice(7));
        if(/^(v |vn |vt |f )/.test(line))geometry.push(line);
      }
      objs.push({file:path.relative(root,p),path:p,bytes:data.length,sha256:sha(data),geometrySha256:sha(geometry.join('\n')),verts,faces,tris,uvs,min,max,mtllib:[...libs],missingMtllib:[...libs].filter(l=>!fs.existsSync(path.join(path.dirname(p),l))),materials:[...materials]});
    }else if(ext==='.glb'){
      const data=fs.readFileSync(p),g=JSON.parse(data.subarray(20,20+data.readUInt32LE(12)).toString('utf8').trim());
      glbs.push({file:path.relative(root,p),path:p,bytes:data.length,sha256:sha(data),asset:g.asset,meshes:g.meshes?.length,skins:g.skins?.length??0,animations:(g.animations??[]).map(a=>a.name),images:g.images?.length??0,materials:(g.materials??[]).map(m=>m.name)});
    }
  }
  const duplicates=Object.values(Object.groupBy(objs,o=>o.geometrySha256)).filter(g=>g.length>1).map(g=>g.map(o=>o.file));
  records.push({scope,files:files.map(p=>({file:path.relative(root,p),path:p,bytes:fs.statSync(p).size})),formats:Object.fromEntries(Object.entries(Object.groupBy(files,p=>path.extname(p))).map(([e,v])=>[e,v.length])),licenseFiles:files.filter(p=>/license|licen[cç]a|author|credits|attribution|readme|\.txt$|\.html$/i.test(p)),objs,glbs,geometryDuplicates:duplicates});
}
const report=path.join(project,'reports/new_delivery_20261006');fs.mkdirSync(report,{recursive:true});
fs.writeFileSync(path.join(report,'source_audit.json'),JSON.stringify({sourceRoot:root,date:new Date().toISOString(),readOnlySource:true,records},null,2));
for(const r of records)console.log(JSON.stringify({scope:r.scope,formats:r.formats,duplicateGroups:r.geometryDuplicates,parts:r.objs.map(o=>({file:o.file.split('\\').slice(-2).join('/'),tris:o.tris,uvs:o.uvs,min:o.min,max:o.max})),glbs:r.glbs}));
