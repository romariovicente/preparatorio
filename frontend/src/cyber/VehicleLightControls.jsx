import {AUXILIARY_LIGHTS,HEADLIGHT_MODES,readVehicleLights} from './vehicleLighting.js';

export default function VehicleLightControls({profile,value,powered,onChange}) {
  const {mode,auxiliaries}=readVehicleLights(profile,value);
  return <fieldset className="cyber-vehicle-lights" data-vehicle-lights-mode={mode}
    data-vehicle-lights-powered={powered}>
    <legend>Iluminação do veículo</legend>
    <label>Faróis
      <select value={mode} onChange={event=>onChange({mode:event.target.value})}>
        {Object.entries(HEADLIGHT_MODES).map(([id,label])=><option key={id} value={id}>{label}</option>)}
      </select>
    </label>
    {mode==='drl'&&!powered&&<small>A luz diurna acende ao ligar o motor.</small>}
    {Object.entries(auxiliaries).map(([id,enabled])=><label key={id}>
      <input type="checkbox" checked={enabled} onChange={event=>onChange({auxiliary:id,enabled:event.target.checked})}/>
      {AUXILIARY_LIGHTS[id]}
    </label>)}
  </fieldset>;
}
