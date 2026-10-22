export type EstadoTarefa = 'esperando' | 'em_andamento' | 'concluido';

export interface Tarefa {
  id?: number;
  usuario_id: number;
  nome: string;
  descricao: string;
  data_prazo: string;
  estado: EstadoTarefa;
}
