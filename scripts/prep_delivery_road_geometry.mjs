// Export only derived road geometry. The source GLB and .blend are never opened
// for writing. A Blender importer should map [X,Z] to (X,-Z,surfaceY).
import {mkdirSync,writeFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {buildDeliveryRoadSurfaces,newDeliveryRoadConnections} from '../frontend/src/cyber/newDeliveryWorld.js';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const output=resolve(root,'reports/new_delivery_roads_20261008.json');
const surfaces=buildDeliveryRoadSurfaces().map(surface=>{
  const xs=surface.points.map(p=>p[0]),zs=surface.points.map(p=>p[1]);
  const minX=Math.min(...xs),maxX=Math.max(...xs),minZ=Math.min(...zs),maxZ=Math.max(...zs);
  return {...surface,center:[(minX+maxX)/2,surface.surfaceY,(minZ+maxZ)/2],boundsSize:[maxX-minX,maxZ-minZ],
    blenderVertices:surface.points.map(([x,z])=>[x,-z,surface.surfaceY])};
});
const report={version:1,date:'2026-10-08',units:'meters',coordinateMap:'Three [X,Y,Z] -> Blender [X,-Z,Y]',
  sourcePreserved:true,...newDeliveryRoadConnections,surfaces,
  renderBatches:new Set(surfaces.map(s=>`${s.material}-${s.surfaceY}`)).size,
  note:'Polygon faces are authoritative. Bounds are only enclosing dimensions for clipped or diagonal fragments. Assign source materials, mark floors walkable, and add no solid barrier.'};
mkdirSync(dirname(output),{recursive:true});writeFileSync(output,`${JSON.stringify(report,null,2)}\n`);
console.log(JSON.stringify({output,surfaces:surfaces.length,renderBatches:report.renderBatches,streets:report.streets,cycleLanes:report.cycleLanes,pedestrianLinks:report.pedestrianLinks}));
