import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Textarea } from './components/ui/textarea';
import { Switch } from './components/ui/switch';
import { toast } from './hooks/use-toast';
import ContentScheduler from './ContentScheduler';
import { 
  DollarSign, 
  Users, 
  FileText, 
  TrendingUp, 
  Upload, 
  Plus,
  BarChart3,
  Calendar,
  Gift,
  Clock
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = ({ user }) => {
  const [stats, setStats] = useState({
    subscriber_count: 0,
    content_count: 0,
    total_revenue: 0,
    follower_count: 0
  });
  const [contentForm, setContentForm] = useState({
    title: '',
    description: '',
    is_premium: false,
    is_ppv: false,
    ppv_price: '',
    tags: '',
    file: null
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user?.is_creator) {
      fetchStats();
    }
  }, [user]);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/creator/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleContentSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('title', contentForm.title);
      formData.append('description', contentForm.description);
      formData.append('is_premium', contentForm.is_premium);
      formData.append('is_ppv', contentForm.is_ppv);
      formData.append('ppv_price', contentForm.ppv_price || '0');
      formData.append('tags', contentForm.tags);
      
      if (contentForm.file) {
        formData.append('file', contentForm.file);
      }

      await axios.post(`${API}/content`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      toast({ 
        title: "¡Contenido creado exitosamente!",
        description: "Tu contenido ya está disponible para tus fans."
      });

      // Reset form
      setContentForm({
        title: '',
        description: '',
        is_premium: false,
        is_ppv: false,
        ppv_price: '',
        tags: '',
        file: null
      });

      // Refresh stats
      fetchStats();
    } catch (error) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Error al crear contenido",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  if (!user?.is_creator) {
    return (
      <div className="max-w-2xl mx-auto py-16 px-4 text-center">
        <div className="bg-yellow-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-6">
          <Users className="h-8 w-8 text-yellow-600" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900 mb-4">Acceso de Creador Requerido</h1>
        <p className="text-slate-600 mb-8">Esta sección está disponible solo para usuarios registrados como creadores.</p>
        <Button onClick={() => window.location.href = '/explore'}>
          Explorar Creadores
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Dashboard de Creador</h1>
        <p className="text-slate-600">Gestiona tu contenido y analiza tu rendimiento</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Ingresos Totales</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${stats.total_revenue?.toFixed(2) || '0.00'}</div>
            <p className="text-xs text-muted-foreground">+20.1% desde el mes pasado</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Suscriptores</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.subscriber_count || 0}</div>
            <p className="text-xs text-muted-foreground">+180 nuevos este mes</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Contenidos</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.content_count || 0}</div>
            <p className="text-xs text-muted-foreground">+12 este mes</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Seguidores</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.follower_count || 0}</div>
            <p className="text-xs text-muted-foreground">+12% crecimiento</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs Content */}
      <Tabs defaultValue="upload" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="upload">Subir Contenido</TabsTrigger>
          <TabsTrigger value="schedule">Programar Contenido</TabsTrigger>
          <TabsTrigger value="analytics">Analíticas</TabsTrigger>
          <TabsTrigger value="earnings">Ganancias</TabsTrigger>
        </TabsList>

        {/* Upload Content Tab */}
        <TabsContent value="upload">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Upload className="h-5 w-5 mr-2" />
                Crear Nuevo Contenido
              </CardTitle>
              <CardDescription>
                Sube contenido para tus suscriptores. Puedes hacerlo gratuito, premium o pago por visualización.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleContentSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="title">Título *</Label>
                    <Input
                      id="title"
                      value={contentForm.title}
                      onChange={(e) => setContentForm({ ...contentForm, title: e.target.value })}
                      placeholder="Título de tu contenido"
                      required
                    />
                  </div>
                  
                  <div>
                    <Label htmlFor="tags">Tags (separados por comas)</Label>
                    <Input
                      id="tags"
                      value={contentForm.tags}
                      onChange={(e) => setContentForm({ ...contentForm, tags: e.target.value })}
                      placeholder="fitness, lifestyle, motivación"
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="description">Descripción *</Label>
                  <Textarea
                    id="description"
                    value={contentForm.description}
                    onChange={(e) => setContentForm({ ...contentForm, description: e.target.value })}
                    placeholder="Describe tu contenido..."
                    rows={4}
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="file">Archivo (imagen, video, audio)</Label>
                  <Input
                    id="file"
                    type="file"
                    accept="image/*,video/*,audio/*"
                    onChange={(e) => setContentForm({ ...contentForm, file: e.target.files[0] })}
                  />
                </div>

                <div className="space-y-4">
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="is_premium"
                      checked={contentForm.is_premium}
                      onCheckedChange={(checked) => setContentForm({ ...contentForm, is_premium: checked })}
                    />
                    <Label htmlFor="is_premium">Contenido Premium (solo para suscriptores)</Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Switch
                      id="is_ppv"
                      checked={contentForm.is_ppv}
                      onCheckedChange={(checked) => setContentForm({ ...contentForm, is_ppv: checked })}
                    />
                    <Label htmlFor="is_ppv">Pago por Visualización (PPV)</Label>
                  </div>

                  {contentForm.is_ppv && (
                    <div className="ml-6">
                      <Label htmlFor="ppv_price">Precio PPV ($USD)</Label>
                      <Input
                        id="ppv_price"
                        type="number"
                        step="0.01"
                        min="1"
                        value={contentForm.ppv_price}
                        onChange={(e) => setContentForm({ ...contentForm, ppv_price: e.target.value })}
                        placeholder="5.00"
                      />
                    </div>
                  )}
                </div>

                <Button type="submit" disabled={loading} className="w-full">
                  {loading ? 'Subiendo...' : (
                    <>
                      <Plus className="h-4 w-4 mr-2" />
                      Crear Contenido
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <BarChart3 className="h-5 w-5 mr-2" />
                  Rendimiento del Contenido
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-slate-600">Visualizaciones totales</span>
                    <span className="font-semibold">12.4K</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-slate-600">Tasa de engagement</span>
                    <span className="font-semibold">8.2%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-slate-600">Contenido más popular</span>
                    <span className="font-semibold">Rutina matutina</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Calendar className="h-5 w-5 mr-2" />
                  Actividad Reciente
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center space-x-3">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm">Nuevo suscriptor: Ana M.</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <span className="text-sm">Contenido publicado: Yoga para principiantes</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                    <span className="text-sm">Propina recibida: $15.00</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Earnings Tab */}
        <TabsContent value="earnings">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <DollarSign className="h-5 w-5 mr-2" />
                  Resumen de Ganancias
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">${stats.total_revenue?.toFixed(2) || '0.00'}</div>
                      <div className="text-sm text-slate-600">Total ganado</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-600">$245.80</div>
                      <div className="text-sm text-slate-600">Este mes</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-600">$89.20</div>
                      <div className="text-sm text-slate-600">Esta semana</div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Gift className="h-5 w-5 mr-2" />
                  Fuentes de Ingreso
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm">Suscripciones</span>
                    <span className="font-semibold">65%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm">Propinas</span>
                    <span className="font-semibold">25%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm">PPV</span>
                    <span className="font-semibold">10%</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Dashboard;