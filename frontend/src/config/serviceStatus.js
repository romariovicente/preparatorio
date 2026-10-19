export function clockSourceLabel(status){
  if(status==='synced')return 'horário sincronizado com o serviço PREPARATÓRIO';
  if(status==='stale')return 'último horário recebido do serviço PREPARATÓRIO';
  if(status==='connecting')return 'consultando o relógio do serviço PREPARATÓRIO';
  return 'horário deste dispositivo · sem fonte de tempo compartilhada';
}

export function sharedServiceLabel(status,players=1){
  return status==='connected'
    ?`${players} jogador${players===1?'':'es'} na sala compartilhada`
    :'Exploração individual · serviço compartilhado desconectado';
}

export function cityLoadLabel({environment=false,character=false,loaded=0,total=0,progress=0,failed=false,slow=false}={}){
  if(failed)return 'Falha ao carregar um modelo essencial. Recarregue a cidade para tentar novamente.';
  const core=`Cenário ${environment?'pronto':'carregando'} · personagem ${character?'pronto':'carregando'}`;
  const count=Number.isFinite(total)&&total>0?` · recursos 3D: ${Math.max(0,loaded)}/${total} (${Math.round(Math.max(0,Math.min(100,Number.isFinite(progress)?progress:0)))}%)`:'';
  return core+count+(slow?' · o primeiro carregamento transfere cerca de 52 MB; aguarde a conexão.':'');
}
