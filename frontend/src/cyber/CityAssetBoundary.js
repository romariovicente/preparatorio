import {Component,Suspense,createElement} from 'react';
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
  render(){return this.state.failed?null:this.props.children;}
}

// Each secondary model owns its pending/error state. A distant vehicle or
// interior must not prevent the already loaded ground and player from committing.
export default function CityAssetBoundary({children,label='objeto da cidade',assetUrls}){
  return createElement(OptionalAssetErrorBoundary,{label,assetUrls},createElement(Suspense,{fallback:null},children));
}
