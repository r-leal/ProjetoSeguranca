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

/** Claims decodificadas do JWT salvo no localStorage (ver AuthService). */
export interface UsuarioToken {
  id: number;
  nome: string;
  sobrenome: string;
  email: string;
  papel: Papel;
}
