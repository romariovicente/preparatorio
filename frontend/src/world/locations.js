// Deliberate game landmarks fitted to the supplied mesh, not real geographic coordinates.
export const categories = [
  {id:'all', name:'Todos'}, {id:'education',name:'Educação'},
  {id:'health',name:'Saúde'}, {id:'city',name:'Cidade'},
  {id:'nature',name:'Natureza'}, {id:'transport',name:'Transporte'},
];
const palette={education:'#61d8e3',health:'#ff8193',city:'#d7b6fa',nature:'#83d3a4',transport:'#f4ca7a'};
export const locations = [
  {id:'senac',name:'SENAC',subtitle:'Educação profissional',category:'education',symbol:'S',position:[-86,43],description:'Seu primeiro destino na trilha de formação. Conheça a ilha e prepare-se para as atividades de comunicação em saúde.'},
  {id:'ufal',name:'UFAL',subtitle:'Campus A. C. Simões',category:'education',symbol:'U',position:[-60,-10],description:'Um ponto de encontro para educação, ciência e pesquisa no universo do PREPARATÓRIO.'},
  {id:'hospital',name:'Hospital Universitário',subtitle:'Aprender com cuidado',category:'health',symbol:'+',position:[8,-49],description:'Acesse o laboratório já disponível de comunicação hospitalar, com exercícios fictícios de organização de informações.'},
  {id:'ifal',name:'IFAL',subtitle:'Instituto Federal',category:'education',symbol:'I',position:[111,18],description:'Tecnologia, formação e novas possibilidades. Destino de referência para futuras trilhas profissionais.'},
  {id:'upa',name:'UPA',subtitle:'Unidade de pronto atendimento',category:'health',symbol:'+',position:[78,-16],description:'Marco de saúde da ilha. Os ambientes internos e as simulações específicas serão construídos nas próximas etapas.'},
  {id:'samu',name:'Base do SAMU',subtitle:'Rede de urgência',category:'health',symbol:'+',position:[100,-39],description:'Base de referência para a futura integração de veículos e missões de atendimento simulado.'},
  {id:'plaza',name:'Praça do Conhecimento',subtitle:'O coração da ilha',category:'city',symbol:'✦',position:[34,30],description:'A praça monumental com o cérebro e esculturas do seu mapa. Um símbolo de estudo, prática e evolução.'},
  {id:'shopping',name:'Maceió Shopping',subtitle:'Comércio e convivência',category:'city',symbol:'M',position:[53,-34],description:'Um dos marcos comerciais do mapa conceitual. Lojas e interiores ainda não são interativos.'},
  {id:'residential',name:'Conjunto residencial',subtitle:'Um lugar para chamar de seu',category:'city',symbol:'⌂',position:[-78,98],description:'Área reservada à futura experiência de moradia, inventário e convivência entre jogadores.'},
  {id:'stadium',name:'Estádio Rei Pelé',subtitle:'Lazer e esporte',category:'city',symbol:'●',position:[-40,158],description:'O estádio na região sul da ilha amplia os espaços de encontro e lazer.'},
  {id:'park',name:'Parque Municipal',subtitle:'Verde dentro da cidade',category:'nature',symbol:'♧',position:[-133,10],description:'Vegetação e lagos na borda oeste do modelo. Um ponto para explorar a paisagem da ilha.'},
  {id:'mountains',name:'Serra da Pintada',subtitle:'Paisagem de referência',category:'nature',symbol:'△',position:[-95,-82],description:'A região montanhosa do mapa fornecido. Nome e posição seguem a proposta conceitual da ilha.'},
  {id:'beach',name:'Praia de Ponta Verde',subtitle:'Encontro com o mar',category:'nature',symbol:'≈',position:[12,152],description:'Faixa costeira do mapa temático. Navegação marítima e mergulho ainda não estão implementados.'},
  {id:'airport',name:'Aeroporto Zumbi dos Palmares',subtitle:'Novos horizontes',category:'transport',symbol:'↗',position:[8,-152],description:'O aeroporto aparece no extremo norte do modelo. Veículos, voos e viagens serão etapas futuras.'},
  {id:'port',name:'Porto de Maceió',subtitle:'Conexões pelo mar',category:'transport',symbol:'⚓',position:[141,20],description:'Estruturas portuárias da costa leste, preservadas na versão otimizada do seu modelo.'},
  {id:'bridge',name:'Ponte do Francês',subtitle:'Ligando caminhos',category:'transport',symbol:'↔',position:[130,126],description:'A ponte do modelo original. Sua posição é uma referência de jogo, não uma orientação para deslocamentos reais.'},
].map(point => ({...point,color:palette[point.category]}));

export const locationIds = locations.map(p => p.id);
