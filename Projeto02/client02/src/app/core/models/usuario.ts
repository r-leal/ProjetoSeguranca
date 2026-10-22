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

/** Claims decodificadas do access token mantido em memória (ver AuthService) — só para exibição, nunca validadas no cliente. */
export interface UsuarioToken {
  id: number;
  nome: string;
  sobrenome: string;
  email: string;
  papel: Papel;
}
