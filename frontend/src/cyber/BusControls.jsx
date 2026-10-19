export default function BusControls({bus,occupied,role,nearby,onBoard,onAction,onClear}){
  if(!bus)return null;
  const stopped=Boolean(bus.stopped);
  return <aside className="cyber-car-context cyber-bus-context" aria-label="Interação com o ônibus" data-bus-id={bus.id}>
    <div><strong>{bus.label}</strong>{!occupied&&<button aria-label="Desmarcar ônibus" onClick={onClear}>×</button>}</div>
    <p>{role==='driver'?'Você está ao volante':stopped?'Ônibus parado para embarque':'Ônibus em circulação'}</p>
    <small>{bus.nextStop?`Próxima parada: ${bus.nextStop}`:'Linha PREPARATÓRIO'}</small>
    {bus.id==='bus-brt'&&bus.stopId==='terminal'&&<small>Terminal · acesso a pé pela passagem da Via Oeste.</small>}
    {bus.returnBlocked&&<p>Retorno bloqueado. Assuma o volante e reposicione o ônibus em uma via livre.</p>}
    {!occupied?<><button disabled={!nearby||!stopped||!bus.doorOpen} onClick={onBoard}>Embarcar no ônibus · F</button><small>{!nearby?'Aproxime-se do ônibus na parada.':stopped&&bus.doorOpen?'Embarque como passageiro e escolha se quer dirigir.':'Aguarde o ônibus parar e abrir as portas para embarcar.'}</small></>:<div className="cyber-action-grid">
      {role==='driver'?<><button onClick={()=>onAction('BUS_ENGINE')}>{bus.engineOn?'Desligar':'Ligar'} motor do ônibus</button><button onClick={()=>onAction('BUS_STOP')}>Frear ônibus</button><button disabled={!stopped} onClick={()=>onAction('BUS_RELEASE_WHEEL')}>Devolver volante ao motorista</button></>:<button disabled={!stopped} onClick={()=>onAction('BUS_TAKE_WHEEL')}>Assumir volante</button>}
      <button disabled={!stopped||!bus.doorOpen} onClick={()=>onAction('EXIT')}>Desembarcar · F</button>
    </div>}
    {role==='driver'&&<small>WASD ou setas para dirigir. Pare antes de desembarcar ou devolver o volante.</small>}
  </aside>;
}
