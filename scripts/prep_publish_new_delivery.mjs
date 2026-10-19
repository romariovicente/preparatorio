// Publish only successfully reimported, inspected delivery files.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const reports=path.join(root,'reports/new_delivery_20261006');
const ids=['VEH_Bus_City_20261006','VEH_Bus_BRT_20261006','MOD_Bus_Stop_20261006','BLD_Bus_Terminal_20261006','CHAR_Student_XVIII_20261006','EDU_Anatomy_XRay_20261006'];
const assets=[];
for(const id of ids){
 const r=JSON.parse(fs.readFileSync(path.join(reports,id+'.json'),'utf8'));
 if(r.status!=='validated'||!r.previewRendered)throw new Error(id+' is not validated with a rendered preview');
 const file=path.join(root,'frontend/public',r.url),data=fs.readFileSync(file);
 const hash=crypto.createHash('sha256').update(data).digest('hex');
 if(hash!==r.sha256||data.length!==r.bytes)throw new Error(id+' has changed after reimport validation');
 if(!fs.existsSync(r.preview)||!fs.existsSync(r.blend))throw new Error(id+' has missing blend/preview');
 // Prior converters use Blender XYZ dimension order: height is dimensions[2].
 assets.push({...r,static:true,height:r.dimensions[2],dimensionsOrder:'Blender XYZ = width,depth,height',gltfDimensions:[r.dimensions[0],r.dimensions[2],r.dimensions[1]],
  ...(id==='CHAR_Student_XVIII_20261006'?{figures:2,rigStatus:'Two historical photogrammetry figures side by side; no skeleton or animation; cultural static display, not claimed playable'}:{}),
  preview:'/assets/new-delivery/'+id+'.preview.png'});
 fs.copyFileSync(r.preview,path.join(root,'frontend/public/assets/new-delivery',id+'.preview.png'));
}
const destination=path.join(root,'frontend/src/config/newDeliveryAssets.json');
if(fs.existsSync(destination)){
 const checkpoint=path.join(reports,'newDeliveryAssets_before_publish.json');
 if(!fs.existsSync(checkpoint))fs.copyFileSync(destination,checkpoint);
}
fs.writeFileSync(destination,JSON.stringify(assets,null,2)+'\n');
console.log(JSON.stringify({destination,count:assets.length,assets:assets.map(a=>({id:a.id,url:a.url,height:a.height,triangles:a.triangles,sha256:a.sha256}))},null,2));
