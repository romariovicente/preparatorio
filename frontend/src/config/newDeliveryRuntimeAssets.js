import {resolveAssetReferences} from './deploymentConfig.js';
import deliveredRaw from './newDeliveryAssets.json' with {type:'json'};
const delivered=resolveAssetReferences(deliveredRaw);
const categories={bus:'Veículos',stop:'Cenários',terminal:'Edifícios',character:'Personagens',anatomy:'Anatomia'};
export const newDeliveryRuntimeAssets=delivered.filter(asset=>asset.status==='validated'&&asset.previewRendered).map(asset=>({
  ...asset,name:asset.label,category:categories[asset.category]??'Cenários',sourceCategory:asset.category,
  credits:{...asset.sourceCredits},licenseStatus:asset.sourceCredits?.license?.startsWith('CC-BY-4.0')?'attribution':'unverified',
  sourceLicenseStatus:asset.licenseStatus,animated:false,animations:[],rigged:false,originalRig:false,playable:false,reimportValidated:true,
  visualStyle:'realistic',description:asset.id==='CHAR_Student_XVIII_20261006'
    ?'Dois estudantes históricos digitalizados para exposição cultural. Sem rig ou animação.'
    :asset.licenseStatus.includes('No license')?'Fonte local preservada. Materiais reconstruídos; biblioteca MTL e licença ausentes no OBJ recebido.':'Fonte local preservada; derivado reimportado e inspecionado.'
}));
