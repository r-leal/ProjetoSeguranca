export type Papel = 'usuario' | 'admin' | 'gerente';

export interface Usuario {
  id?: number;
  nome: string;
  sobrenome: string;
  data_nascimento?: string;
  email: string;
  senha: string;
  papel?: Papel;
}
