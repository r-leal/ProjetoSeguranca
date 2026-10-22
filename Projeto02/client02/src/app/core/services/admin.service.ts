import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Usuario } from '../models/usuario';
import { API_BASE_URL } from '../api.config';

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  constructor(private http: HttpClient) {}

  // Esta chamada só é oferecida na UI para quem está logado como admin,
  // mas quem garante isso de fato é o backend: GET /api/usuarios agora
  // exige @papel_required(Usuario.PAPEL_ADMIN), devolvendo 403 para
  // qualquer outro papel autenticado, mesmo chamando a URL direto
  // (curl/DevTools). Ver
  // Documentação/Projeto02/SegurancaAutorizacaoAcesso.md (seção 3); para a
  // falha original, ver Documentação/Projeto01/Vulnerabilidades.md.
  listarUsuarios(termo?: string): Observable<Usuario[]> {
    const url = termo
      ? `${API_BASE_URL}/usuarios?q=${encodeURIComponent(termo)}`
      : `${API_BASE_URL}/usuarios`;
    return this.http.get<Usuario[]>(url);
  }
}
