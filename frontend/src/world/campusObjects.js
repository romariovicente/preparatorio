import {campusObstacles} from './movement.js';
export const CAMPUS_START={x:0,y:0,z:6};
export const campusTemplates = [
  {id:'campus_kit',name:'Kit hospitalar',kind:'kit',position:{x:-3,y:0,z:3},portable:true,movable:false,description:'Uma cópia do kit acompanha seu personagem. O equipamento base continua disponível.',actionLabel:'Conferir materiais',actionText:'Materiais conferidos no exercício. Esta ação representa organização do kit.'},
  {id:'campus_supplies',name:'Caixa de materiais',kind:'supplies',position:{x:3,y:0,z:3},portable:true,movable:false,description:'Caixa de materiais para praticar pegar, carregar e colocar objetos.',actionLabel:'Organizar materiais',actionText:'Materiais organizados. Você pode carregar sua cópia até outra posição.'},
  {id:'campus_cart',name:'Carrinho hospitalar',kind:'cart',position:{x:3,y:0,z:-1},portable:false,movable:true,description:'Uma cópia do carrinho pode ser colocada em um espaço livre próximo ao personagem.',actionLabel:'Examinar carrinho',actionText:'Carrinho examinado. Você pode mover sua cópia para organizar a área.'},
  {id:'campus_chair',name:'Cadeira de apoio',kind:'chair',position:{x:-3,y:0,z:0},portable:false,movable:true,description:'Crie e reposicione sua cópia da cadeira para organizar a área de apoio.',actionLabel:'Examinar cadeira',actionText:'Cadeira examinada. Sua cópia pode ser reposicionada.'},
];
export const campusInteractionOptions = {bounds:{minX:-9,maxX:9,minZ:-8,maxZ:9},obstacles:campusObstacles,placementRadius:.5,reach:2.25,dropReach:2,moveReach:3,maxCopies:20};
