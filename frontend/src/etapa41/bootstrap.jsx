import { createRoot } from 'react-dom/client';
import Launcher from './Launcher.jsx';
import css from './style.css?inline';

const hostId = 'preparatorio-etapa41';

if (!document.getElementById(hostId)) {
  const host = document.createElement('div');
  host.id = hostId;
  document.body.append(host);

  // Isola os estilos do laboratório dos estilos existentes do jogo.
  const shadow = host.attachShadow({ mode: 'open' });
  const style = document.createElement('style');
  style.textContent = css;

  const mount = document.createElement('div');
  shadow.append(style, mount);

  const root = createRoot(mount);
  root.render(<Launcher />);

  if (import.meta.hot) {
    import.meta.hot.dispose(() => {
      root.unmount();
      host.remove();
    });
  }
}
