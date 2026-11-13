import {Children,Component,Suspense,createElement} from 'react';
import {assetRecoveryStore} from './assetRecovery.js';

class OptionalAssetErrorBoundary extends Component {
  state={failed:false};
  failureKey=Symbol('optional-city-asset');
  unregister=null;
  static getDerivedStateFromError(){return {failed:true};}
  componentDidCatch(error){
    console.warn(`Modelo secundário indisponível: ${this.props.label}`);
    this.unregister?.();
    this.unregister=assetRecoveryStore.register({key:this.failureKey,error,urls:this.props.assetUrls,
      retry:()=>this.setState({failed:false})});
  }
  componentWillUnmount(){this.unregister?.();}
  render(){return this.state.failed?this.props.fallback:this.props.children;}
}

// Each secondary model owns its pending/error state. A distant vehicle or
// interior must not prevent the already loaded ground and player from committing.
export default function CityAssetBoundary({children,label='objeto da cidade',assetUrls,fallback=null}){
  return createElement(OptionalAssetErrorBoundary,{label,assetUrls,fallback},createElement(Suspense,{fallback},children));
}

// The world container must never suspend all ready siblings for one model.
// Children.toArray also flattens mapped vehicle/prop arrays into separate limits.
export function CityAssetGroup({children,label='objetos da cidade'}){
  return createElement('group',null,Children.toArray(children).map((child,index)=>{
    const name=child.props?.label??child.type?.displayName??child.type?.name??index;
    return createElement(CityAssetBoundary,{key:child.key??index,label:`${label} · ${name}`,assetUrls:child.props?.assetUrls},child);
  }));
}
