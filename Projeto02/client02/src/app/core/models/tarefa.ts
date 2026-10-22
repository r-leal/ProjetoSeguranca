export type EstadoTarefa = 'esperando' | 'em_andamento' | 'concluido';

export interface Tarefa {
  id?: number;
  usuario_id: number;
  nome: string;
  descricao: string;
  data_prazo: string;
  estado: EstadoTarefa;
  /** Link opcional de referência. O título é sempre o que o backend buscou
   * (ver tarefas/link_preview.py) — nunca um valor definido pelo cliente. */
  url?: string | null;
  url_titulo?: string | null;
}

export interface PreviewLink {
  url: string;
  titulo: string;
}
