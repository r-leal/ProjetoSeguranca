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

  // VULNERABILIDADE PROPOSITAL (Projeto01 — Broken Access Control): esta
  // chamada só é oferecida na UI para quem está logado como admin, mas o
  // backend (GET /api/usuarios) não confere papel nenhum — só exige um JWT
  // válido. Qualquer usuário autenticado que chame esta mesma URL direto
  // (curl/DevTools) recebe a lista completa. Ver
  // Documentação/Projeto01/Vulnerabilidades.md.
  listarUsuarios(termo?: string): Observable<Usuario[]> {
    const url = termo
      ? `${API_BASE_URL}/usuarios?q=${encodeURIComponent(termo)}`
      : `${API_BASE_URL}/usuarios`;
    return this.http.get<Usuario[]>(url);
  }
}
