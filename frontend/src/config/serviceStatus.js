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
