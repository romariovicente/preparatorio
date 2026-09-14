import {
  Component,
  lazy,
  Suspense,
  useEffect,
  useRef,
  useState,
} from 'react';
import ClinicalLab from './ClinicalLab.jsx';

const HospitalScene = lazy(() => import('./HospitalScene.jsx'));

class SceneBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed
      ? (
        <p role="status">
          Cena 3D indisponível. O laboratório continua funcionando.
        </p>
      )
      : this.props.children;
  }
}

export default function Launcher() {
  const [open, setOpen] = useState(false);
  const dialog = useRef(null);
  const activity = useRef(null);

  useEffect(() => {
    const element = dialog.current;
    if (open && !element.open) element.showModal();
    if (!open && element.open) element.close();
  }, [open]);

  function focusActivity() {
    activity.current?.focus();
  }

  return (
    <>
      <button
        className="launch"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
      >
        Hospital · Etapa 41
      </button>

      <dialog
        ref={dialog}
        aria-labelledby="stage-title"
        onCancel={event => {
          event.preventDefault();
          setOpen(false);
        }}
        onKeyDown={event => event.stopPropagation()}
      >
        <header>
          <div>
            <small>PREPARATÓRIO · ETAPA 41</small>
            <h1 id="stage-title">Comunicação hospitalar</h1>
          </div>
          <button onClick={() => setOpen(false)}>
            Voltar ao jogo
          </button>
        </header>

        <div className="layout">
          <section className="scene" aria-label="Sala hospitalar 3D">
            {open && (
              <SceneBoundary>
                <Suspense fallback={<p>Carregando a sala 3D…</p>}>
                  <HospitalScene onInteract={focusActivity} />
                </Suspense>
              </SceneBoundary>
            )}

            <div className="scene-tools">
              <span>
                Arraste para girar · Role ou pince para aproximar
              </span>
              <button onClick={focusActivity}>
                Começar atividade
              </button>
            </div>
          </section>

          <div className="activity" ref={activity} tabIndex={-1}>
            <ClinicalLab />
          </div>
        </div>
      </dialog>
    </>
  );
}
