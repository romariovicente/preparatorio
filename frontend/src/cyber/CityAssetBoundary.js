import {Component,Suspense,createElement} from 'react';

class OptionalAssetErrorBoundary extends Component {
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  componentDidCatch(){console.warn(`Modelo secundário indisponível: ${this.props.label}`);}
  render(){return this.state.failed?null:this.props.children;}
}

// Each secondary model owns its pending/error state. A distant vehicle or
// interior must not prevent the already loaded ground and player from committing.
export default function CityAssetBoundary({children,label='objeto da cidade'}){
  return createElement(OptionalAssetErrorBoundary,{label},createElement(Suspense,{fallback:null},children));
}
