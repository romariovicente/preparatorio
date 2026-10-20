import cityLivingWorld from './cityLivingWorld.json' with {type:'json'};

// Movement and garage placement share the same configured city perimeter.
// This dependency contains no simulation or vehicle imports.
export const playableCityBounds=Object.freeze({...cityLivingWorld.district.requiredPlayableBounds});
