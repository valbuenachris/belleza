// ============================================================
// Página de Usuarios - CRUD real del personal del SPA
// ============================================================

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { api, ApiError } from '../services/api';
import { User, UserCreate, UserUpdate } from '../types';
import {
  Users as UsersIcon, Plus, Search, Edit, Trash2,
  CheckCircle, XCircle, Shield, Mail, Phone, AlertCircle
} from 'lucide-react';

type TenantRole = Exclude<User['rol'], 'superadmin'>;

const roleLabels: Record<string, string> = {
  admin: 'Administrador',
  manager: 'Gerente',
  receptionist: 'Recepcionista',
  therapist: 'Terapeuta',
  masajista: 'Masajista',
  facialista: 'Facialista',
  esteticista: 'Esteticista',
  cosmetologa: 'Cosmetóloga',
  depiladora: 'Depiladora',
  estilista: 'Estilista',
  peluquera: 'Peluquera',
  colorista: 'Colorista',
  peinadora: 'Peinadora',
  barbero: 'Barbero',
  manicurista: 'Manicurista',
  pedicurista: 'Pedicurista',
  cejista: 'Especialista de Cejas',
  pestañista: 'Especialista de Pestañas',
  maquilladora: 'Maquilladora',
  nutriologa: 'Nutrióloga',
  acupunturista: 'Acupunturista',
  auxiliar: 'Auxiliar',
  cajero: 'Cajero',
};

const roleColors: Record<string, string> = {
  admin: 'bg-emerald-50 text-emerald-700',
  manager: 'bg-blue-50 text-blue-700',
  receptionist: 'bg-amber-50 text-amber-700',
  therapist: 'bg-violet-50 text-violet-700',
  masajista: 'bg-violet-50 text-violet-700',
  facialista: 'bg-rose-50 text-rose-700',
  esteticista: 'bg-rose-50 text-rose-700',
  cosmetologa: 'bg-rose-50 text-rose-700',
  depiladora: 'bg-rose-50 text-rose-700',
  estilista: 'bg-cyan-50 text-cyan-700',
  peluquera: 'bg-cyan-50 text-cyan-700',
  colorista: 'bg-cyan-50 text-cyan-700',
  peinadora: 'bg-cyan-50 text-cyan-700',
  barbero: 'bg-cyan-50 text-cyan-700',
  manicurista: 'bg-orange-50 text-orange-700',
  pedicurista: 'bg-orange-50 text-orange-700',
  cejista: 'bg-orange-50 text-orange-700',
  pestañista: 'bg-orange-50 text-orange-700',
  maquilladora: 'bg-pink-50 text-pink-700',
  nutriologa: 'bg-pink-50 text-pink-700',
  acupunturista: 'bg-pink-50 text-pink-700',
  auxiliar: 'bg-stone-50 text-stone-600',
  cajero: 'bg-stone-50 text-stone-600',
};

const ROLE_OPTIONS = Object.keys(roleLabels).map((key) => ({
  value: key,
  label: roleLabels[key],
}));

export default function UsersPage() {
  const { user: currentUser, tenant } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [filterRole, setFilterRole] = useState<string>('all');
  const [error, setError] = useState('');

  const canManage = currentUser?.rol === 'admin';

  const loadUsers = useCallback(async () => {
    setError('');
    try {
      const data = await api.getUsers();
      setUsers(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al cargar usuarios');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const filteredUsers = users.filter(u => {
    const matchesSearch = u.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.username.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = filterRole === 'all' || u.rol === filterRole;
    return matchesSearch && matchesRole;
  });

  const handleDelete = async (id: string) => {
    if (!confirm('¿Estás seguro de que deseas desactivar este usuario?')) return;
    setError('');
    try {
      await api.deleteUser(id);
      loadUsers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al desactivar usuario');
    }
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600 flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-stone-800">Usuarios</h1>
          <p className="text-stone-500 mt-1">Personal de {tenant?.nombre || 'tu SPA'}</p>
        </div>
        {canManage && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl
              hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-200/50 transition-all"
          >
            <Plus size={18} />
            Nuevo Usuario
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex items-center gap-2 bg-white rounded-xl px-4 py-2.5 border border-stone-200 flex-1 max-w-md">
          <Search size={18} className="text-stone-400" />
          <input
            type="text"
            placeholder="Buscar por nombre, email o usuario..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-none outline-none text-sm text-stone-700 placeholder:text-stone-400 w-full"
          />
        </div>
        <select
          value={filterRole}
          onChange={(e) => setFilterRole(e.target.value)}
          className="px-4 py-2.5 bg-white border border-stone-200 rounded-xl text-sm text-stone-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
        >
          <option value="all">Todos los roles</option>{ROLE_OPTIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
        </select>
      </div>

      {/* Users Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-white rounded-2xl p-6 border border-stone-100 animate-pulse">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-full bg-stone-100" />
                <div className="flex-1">
                  <div className="h-4 bg-stone-100 rounded w-24 mb-2" />
                  <div className="h-3 bg-stone-100 rounded w-32" />
                </div>
              </div>
              <div className="h-3 bg-stone-100 rounded w-20" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredUsers.map((user) => (
            <div
              key={user.id}
              className="bg-white rounded-2xl p-6 border border-stone-100 hover:shadow-lg hover:shadow-stone-100 transition-all duration-300"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-stone-200 to-stone-300 flex items-center justify-center">
                    <span className="text-sm font-bold text-stone-600">
                      {user.nombre[0]}{user.apellido[0]}
                    </span>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-stone-800">{user.nombre} {user.apellido}</p>
                    <p className="text-xs text-stone-500">@{user.username}</p>
                  </div>
                </div>
                <div className="flex gap-0.5">
                  {canManage && (
                    <>
                      <button
                        onClick={() => setEditingUser(user)}
                        className="p-1.5 rounded-lg hover:bg-stone-100 text-stone-400 hover:text-stone-600 transition-colors"
                        title="Editar usuario"
                      >
                        <Edit size={14} />
                      </button>
                      {user.id !== currentUser?.id && (
                        <button
                          onClick={() => handleDelete(user.id)}
                          className="p-1.5 rounded-lg hover:bg-red-50 text-stone-400 hover:text-red-500 transition-colors"
                          title="Desactivar usuario"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs text-stone-500">
                  <Mail size={13} />
                  <span className="truncate">{user.email}</span>
                </div>
                {user.telefono && (
                  <div className="flex items-center gap-2 text-xs text-stone-500">
                    <Phone size={13} />
                    <span>{user.telefono}</span>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between mt-4 pt-4 border-t border-stone-100">
                <span className={`inline-flex px-2.5 py-1 text-xs font-medium rounded-full ${roleColors[user.rol]}`}>
                  <Shield size={12} className="mr-1" />
                  {roleLabels[user.rol]}
                </span>
                {user.activo ? (
                  <span className="inline-flex items-center gap-1 text-xs text-emerald-600">
                    <CheckCircle size={12} /> Activo
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs text-red-500">
                    <XCircle size={12} /> Inactivo
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {filteredUsers.length === 0 && !loading && (
        <div className="text-center py-12 bg-white rounded-2xl border border-stone-100">
          <UsersIcon size={48} className="mx-auto text-stone-300 mb-3" />
          <p className="text-stone-500">No se encontraron usuarios</p>
        </div>
      )}

      {showCreateModal && (
        <CreateUserModal
          onClose={() => setShowCreateModal(false)}
          onCreated={() => { setShowCreateModal(false); loadUsers(); }}
        />
      )}

      {editingUser && (
        <EditUserModal
          user={editingUser}
          onClose={() => setEditingUser(null)}
          onUpdated={() => { setEditingUser(null); loadUsers(); }}
        />
      )}
    </div>
  );
}

// ============================================================
// Modal de Crear Usuario
// ============================================================
function CreateUserModal({ onClose, onCreated }: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    nombre: '',
    apellido: '',
    telefono: '',
    rol: 'receptionist' as TenantRole,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data: UserCreate = {
        username: formData.username,
        email: formData.email,
        password: formData.password,
        nombre: formData.nombre,
        apellido: formData.apellido,
        rol: formData.rol,
        telefono: formData.telefono || null,
      };
      await api.createUser(data);
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al crear usuario');
      setLoading(false);
    }
  };

  const inputClass = "w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-stone-100">
          <h2 className="text-xl font-semibold text-stone-800">Nuevo Usuario</h2>
          <p className="text-sm text-stone-500 mt-1">Agrega un nuevo miembro al equipo</p>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">{error}</div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Nombre *</label>
              <input
                type="text" required value={formData.nombre}
                onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                className={inputClass} placeholder="María"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Apellido *</label>
              <input
                type="text" required value={formData.apellido}
                onChange={(e) => setFormData({ ...formData, apellido: e.target.value })}
                className={inputClass} placeholder="González"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Usuario *</label>
            <input
              type="text" required value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value.toLowerCase().replace(/[^a-z0-9]/g, '') })}
              className={inputClass} placeholder="maria.gonzalez"
            />
            <p className="text-xs text-stone-400 mt-1">Solo letras y números</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Email *</label>
            <input
              type="email" required value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className={inputClass} placeholder="maria@spa.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Contraseña *</label>
            <input
              type="password" required minLength={8} value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className={inputClass} placeholder="Mínimo 8 caracteres"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Teléfono</label>
              <input
                type="tel" value={formData.telefono}
                onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                className={inputClass} placeholder="+57 300 123 4567"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Rol *</label>
              <select
                value={formData.rol}
                onChange={(e) => setFormData({ ...formData, rol: e.target.value as TenantRole })}
                className={inputClass}
              >
                {ROLE_OPTIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>
          </div>
          <div className="flex gap-3 pt-4">
            <button
              type="button" onClick={onClose}
              className="flex-1 py-2.5 border border-stone-200 rounded-xl text-sm font-medium text-stone-600 hover:bg-stone-50"
            >
              Cancelar
            </button>
            <button
              type="submit" disabled={loading}
              className="flex-1 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 transition-all"
            >
              {loading ? 'Creando...' : 'Crear Usuario'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ============================================================
// Modal de Editar Usuario
// ============================================================
function EditUserModal({ user, onClose, onUpdated }: {
  user: User;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [formData, setFormData] = useState({
    nombre: user.nombre,
    apellido: user.apellido,
    telefono: user.telefono || '',
    rol: user.rol as TenantRole,
    activo: user.activo,
    password: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data: UserUpdate = {
        nombre: formData.nombre,
        apellido: formData.apellido,
        telefono: formData.telefono || null,
        rol: formData.rol,
        activo: formData.activo,
      };
      if (formData.password) data.password = formData.password;
      await api.updateUser(user.id, data);
      onUpdated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al actualizar usuario');
      setLoading(false);
    }
  };

  const inputClass = "w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-stone-100">
          <h2 className="text-xl font-semibold text-stone-800">Editar Usuario</h2>
          <p className="text-sm text-stone-500 mt-1">{user.nombre} {user.apellido} — @{user.username}</p>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">{error}</div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Nombre *</label>
              <input
                type="text" required value={formData.nombre}
                onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Apellido *</label>
              <input
                type="text" required value={formData.apellido}
                onChange={(e) => setFormData({ ...formData, apellido: e.target.value })}
                className={inputClass}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Teléfono</label>
            <input
              type="tel" value={formData.telefono}
              onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
              className={inputClass}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Rol *</label>
              <select
                value={formData.rol}
                onChange={(e) => setFormData({ ...formData, rol: e.target.value as TenantRole })}
                className={inputClass}
              >
                {ROLE_OPTIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Estado</label>
              <select
                value={formData.activo ? '1' : '0'}
                onChange={(e) => setFormData({ ...formData, activo: e.target.value === '1' })}
                className={inputClass}
              >
                <option value="1">Activo</option>
                <option value="0">Inactivo</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Nueva contraseña (opcional)</label>
            <input
              type="password" value={formData.password} minLength={8}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className={inputClass} placeholder="Dejar vacío para no cambiar"
            />
          </div>
          <div className="flex gap-3 pt-4">
            <button
              type="button" onClick={onClose}
              className="flex-1 py-2.5 border border-stone-200 rounded-xl text-sm font-medium text-stone-600 hover:bg-stone-50"
            >
              Cancelar
            </button>
            <button
              type="submit" disabled={loading}
              className="flex-1 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 transition-all"
            >
              {loading ? 'Guardando...' : 'Guardar Cambios'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}