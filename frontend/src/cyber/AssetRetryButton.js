import {createElement,useSyncExternalStore} from 'react';
import {assetRecoveryStore} from './assetRecovery.js';

export default function AssetRetryButton(){
  const failures=useSyncExternalStore(assetRecoveryStore.subscribe,assetRecoveryStore.getSnapshot,assetRecoveryStore.getServerSnapshot);
  return failures?createElement('button',{onClick:()=>assetRecoveryStore.retryFailed()},'Tentar carregar objetos novamente'):null;
}
