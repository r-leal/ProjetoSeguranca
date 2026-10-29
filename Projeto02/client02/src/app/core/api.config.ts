// Caminho relativo: o dev-server do Angular (proxy.conf.json) repassa
// /api para http://localhost:8000. Isso faz a página "ver" a chamada como
// mesma origem (localhost:4200), que é exigido pelo HttpXsrfInterceptor do
// Angular para anexar automaticamente o header X-XSRF-TOKEN — ver
// Documentação/Projeto02/SegurancaAutorizacaoAcesso.md (seção 7.3).
export const API_BASE_URL = '/api';
