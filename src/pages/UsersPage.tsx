// ============================================================
// Página de Usuarios - Gestión de usuarios del sistema
// ============================================================

import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { User } from '../types';
import {
  Users as UsersIcon, Plus, Search, Edit, Trash2,
  CheckCircle, XCircle, Shield, Mail, Phone, MoreVertical
} from 'lucide-react';

const roleLabels: Record<string, string> = {
  superadmin: 'Super Administrador',
  admin: 'Administrador',
  manager: 'Gerente',
  receptionist: 'Recepcionista',
  therapist: 'Terapeuta',
};

const roleColors: Record<string, string> = {
  superadmin: 'bg-red-50 text-red-700',
  admin: 'bg-emerald-50 text-emerald-700',
  manager: 'bg-blue-50 text-blue-700',
  receptionist: 'bg-amber-50 text-amber-700',
  therapist: 'bg-violet-50 text-violet-700',
};

export default function UsersPage() {
  const { user: currentUser, tenant } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [filterRole, setFilterRole] = useState<string>('all');

  useEffect(() => {
    loadUsers();
  }, [tenant]);

  const loadUsers = async () => {
    try {
      const data = await api.getUsers(currentUser?.rol === 'superadmin' ? undefined : tenant?.id);
      setUsers(data);
    } catch {
      // Error
    } finally {
      setLoading(false);
    }
  };

  const filteredUsers = users.filter(u => {
    const matchesSearch = u.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.username.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = filterRole === 'all' || u.rol === filterRole;
    return matchesSearch && matchesRole;
  });

  const handleDelete = async (id: string) => {
    if (confirm('¿Estás seguro de que deseas desactivar este usuario?')) {
      await api.deleteUser(id);
      loadUsers();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-stone-800">Usuarios</h1>
          <p className="text-stone-500 mt-1">
            {currentUser?.rol === 'superadmin'
              ? 'Gestiona todos los usuarios del sistema'
              : `Usuarios de ${tenant?.nombre || 'tu SPA'}`}
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl
            hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-200/50 transition-all"
        >
          <Plus size={18} />
          Nuevo Usuario
        </button>
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
          <option value="all">Todos los roles</option>
          <option value="admin">Administrador</option>
          <option value="manager">Gerente</option>
          <option value="receptionist">Recepcionista</option>
          <option value="therapist">Terapeuta</option>
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
                  <button className="p-1.5 rounded-lg hover:bg-stone-100 text-stone-400 hover:text-stone-600 transition-colors">
                    <Edit size={14} />
                  </button>
                  {user.id !== currentUser?.id && (
                    <button
                      onClick={() => handleDelete(user.id)}
                      className="p-1.5 rounded-lg hover:bg-red-50 text-stone-400 hover:text-red-500 transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
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

      {/* Create Modal */}
      {showCreateModal && (
        <CreateUserModal
          tenantId={currentUser?.rol === 'superadmin' ? undefined : tenant?.id}
          onClose={() => setShowCreateModal(false)}
          onCreated={() => { setShowCreateModal(false); loadUsers(); }}
        />
      )}
    </div>
  );
}

// ============================================================
// Modal de Crear Usuario
// ============================================================
function CreateUserModal({ tenantId, onClose, onCreated }: {
  tenantId?: string;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    nombre: '',
    apellido: '',
    rol: 'receptionist' as const,
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.createUser({ ...formData, tenant_id: tenantId });
      onCreated();
    } catch {
      // Error
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-stone-100">
          <h2 className="text-xl font-semibold text-stone-800">Nuevo Usuario</h2>
          <p className="text-sm text-stone-500 mt-1">Agrega un nuevo miembro al equipo</p>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Nombre *</label>
              <input
                type="text"
                required
                value={formData.nombre}
                onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                placeholder="María"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Apellido *</label>
              <input
                type="text"
                required
                value={formData.apellido}
                onChange={(e) => setFormData({ ...formData, apellido: e.target.value })}
                className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                placeholder="González"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Usuario *</label>
            <input
              type="text"
              required
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value.toLowerCase() })}
              className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
              placeholder="maria.gonzalez"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Email *</label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
              placeholder="maria@spa.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Contraseña *</label>
            <input
              type="password"
              required
              minLength={8}
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
              placeholder="Mínimo 8 caracteres"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Rol *</label>
            <select
              value={formData.rol}
              onChange={(e) => setFormData({ ...formData, rol: e.target.value as any })}
              className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
            >
              <option value="admin">Administrador</option>
              <option value="manager">Gerente</option>
              <option value="receptionist">Recepcionista</option>
              <option value="therapist">Terapeuta</option>
            </select>
          </div>
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 border border-stone-200 rounded-xl text-sm font-medium text-stone-600 hover:bg-stone-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
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
