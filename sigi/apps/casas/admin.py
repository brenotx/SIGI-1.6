# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.contenttypes import generic
from django.http import HttpResponse, HttpResponseRedirect

from geraldo.generators import PDFGenerator

from sigi.apps.casas.forms import CasaLegislativaForm
from sigi.apps.casas.models import CasaLegislativa, Presidente, Funcionario, TipoCasaLegislativa
from sigi.apps.casas.reports import CasasLegislativasLabels, CasasLegislativasReport
from sigi.apps.casas.views import report_complete, labels_report, export_csv, \
                                    labels_report_sem_presidente, report, \
                                    adicionar_casas_carrinho
from sigi.apps.utils import queryset_ascii
from sigi.apps.contatos.models import Telefone
from sigi.apps.convenios.models import Projeto, Convenio, EquipamentoPrevisto, Anexo
from sigi.apps.mesas.models import Legislatura
from sigi.apps.diagnosticos.models import Diagnostico
from sigi.apps.inventario.models import Bem
from sigi.apps.servicos.models import Servico
from sigi.apps.metas.models import PlanoDiretor
from sigi.apps.ocorrencias.models import Ocorrencia
from django.utils.translation import ugettext as _


class TelefonesInline(generic.GenericTabularInline):
    model = Telefone
    readonly_fields = ('ult_alteracao',)
    extra = 1

class PresidenteInline(admin.StackedInline):
    model = Presidente
    exclude = ['cargo','funcao']
    readonly_fields = ('ult_alteracao',)
    extra = 1
    max_num = 1
    inlines = (TelefonesInline)

class FuncionariosInline(admin.StackedInline):
    model = Funcionario
    fieldsets = ((None, {
                    'fields': (('nome', 'sexo', 'nota', 'email'), ('cargo', 'funcao', 'setor', 'tempo_de_servico'), 'ult_alteracao') 
                }),)
    readonly_fields = ('ult_alteracao',)				
    extra = 1
    inlines = (TelefonesInline,)
    def queryset(self, request):
        return self.model.objects.exclude(cargo="Presidente")

class ConveniosInline(admin.StackedInline):
    model = Convenio
    fieldsets = (
        (None, {'fields': (('link_convenio', 'num_processo_sf','num_convenio','projeto','observacao'),
                           ('data_adesao', 'data_retorno_assinatura', 'data_termo_aceite', 'data_pub_diario', 'data_devolucao_via', 'data_postagem_correio'),
                           ('data_devolucao_sem_assinatura','data_retorno_sem_assinatura',),
                           ('get_tramitacoes', 'get_anexos', 'get_equipamentos',),
                           )}
        ),
    )
    readonly_fields = ['get_tramitacoes', 'get_anexos', 'get_equipamentos', 'link_convenio',]
    extra = 0
    def get_tramitacoes(self, obj):
        return '<br/>'.join([t.__unicode__() for t in obj.tramitacao_set.all()])
    get_tramitacoes.short_description = 'Tramitações'
    get_tramitacoes.allow_tags = True

    def get_anexos(self, obj):
        return '<br/>'.join(['<a href="%s" target="_blank">%s</a>' % (a.arquivo.url, a.__unicode__()) for a in obj.anexo_set.all()])
    get_anexos.short_description = 'Anexos'
    get_anexos.allow_tags = True
    
    def get_equipamentos(self, obj):
        return '<br/>'.join([e.__unicode__() for e in obj.equipamentoprevisto_set.all()])
    get_equipamentos.short_description = 'Equipamentos previstos'
    get_equipamentos.allow_tags = True
    
    def link_convenio(self, obj):
        if obj.pk is None:
            return ""
        from django.core.urlresolvers import reverse
        url = reverse('admin:%s_%s_change' %(obj._meta.app_label,  obj._meta.module_name),  args=[obj.pk] )
        url = url + '?_popup=1'
        return """<input id="edit_convenio-%s" type="hidden"/> 
          <a id="lookup_edit_convenio-%s" href="%s" class="changelink" onclick="return showRelatedObjectLookupPopup(this)"> 
            Editar
          </a>""" % (obj.pk, obj.pk, url)
    
    link_convenio.short_description = 'Editar convenio'
    link_convenio.allow_tags = True
    
class LegislaturaInline(admin.TabularInline):
    model = Legislatura
    fields = ['numero', 'data_inicio', 'data_fim', 'data_eleicao', 'total_parlamentares', 'link_parlamentares',]
    readonly_fields = ['link_parlamentares',]
    
    def link_parlamentares(self, obj):
        if obj.pk is None:
            return ""
        from django.core.urlresolvers import reverse
        url = reverse('admin:%s_%s_change' %(obj._meta.app_label,  obj._meta.module_name),  args=[obj.pk] )
        url = url + '?_popup=1'
        return """<input id="edit_legislatura-%s" type="hidden"/> 
          <a id="lookup_edit_legislatura-%s" href="%s" class="changelink" onclick="return showRelatedObjectLookupPopup(this)"> 
            Editar
          </a>""" % (obj.pk, obj.pk, url)
    
    link_parlamentares.short_description = 'Parlamentares'
    link_parlamentares.allow_tags = True
    
class DiagnosticoInline(admin.TabularInline):
    model = Diagnostico
    fields = ['data_visita_inicio', 'data_visita_fim', 'publicado', 'data_publicacao', 'responsavel', 'link_diagnostico',]
    readonly_fields = ['data_visita_inicio', 'data_visita_fim', 'publicado', 'data_publicacao', 'responsavel', 'link_diagnostico',]
    extra = 0
    max_num = 0
    can_delete = False
    
    def link_diagnostico(self, obj):
        if obj.pk is None:
            return ""
        from django.core.urlresolvers import reverse
        url = reverse('admin:%s_%s_change' %(obj._meta.app_label,  obj._meta.module_name),  args=["%s.pdf" % obj.pk] )
        return """<input id="edit_diagnostico-%s" type="hidden"/> 
          <a id="lookup_edit_diagnostico-%s" href="%s" class="button" target="_blank"> 
            Abrir PDF
          </a>""" % (obj.pk, obj.pk, url)
    
    link_diagnostico.short_description = 'Ver PDF'
    link_diagnostico.allow_tags = True

class BemInline(admin.TabularInline):
    model = Bem
    
class ServicoInline(admin.TabularInline):
    model = Servico
    fields = ['url', 'contato_tecnico', 'contato_administrativo', 'hospedagem_interlegis', 'data_ativacao', 'data_alteracao', 'data_desativacao']
    readonly_fields = ['url', 'contato_tecnico', 'contato_administrativo', 'hospedagem_interlegis', 'data_ativacao', 'data_alteracao', 'data_desativacao']
    extra = 0
    max_num = 0
    can_delete = False

class PlanoDiretorInline(admin.TabularInline):
    model = PlanoDiretor

class OcorrenciaInline(admin.TabularInline):
    model = Ocorrencia
    fields = ('data_criacao', 'assunto', 'prioridade', 'status', 'data_modificacao', 'setor_responsavel',)
    readonly_fields = ('data_criacao', 'assunto', 'prioridade', 'status', 'data_modificacao', 'setor_responsavel',)
    extra = 0
    max_num = 0
    can_delete = False
    
class CasaLegislativaAdmin(admin.ModelAdmin):
    form = CasaLegislativaForm
    change_form_template = 'casas/change_form.html'
    change_list_template = 'casas/change_list.html'
    actions = ['adicionar_casas',]
    inlines = (TelefonesInline, PresidenteInline, FuncionariosInline, ConveniosInline, LegislaturaInline,
               DiagnosticoInline, BemInline, ServicoInline, PlanoDiretorInline, OcorrenciaInline, )
    list_display = ('nome','municipio','logradouro', 'ult_alt_endereco', 'get_convenios')
    list_display_links = ('nome',)
    list_filter = ('tipo', 'municipio__uf__nome', 'convenio__projeto')
    ordering = ('nome','municipio__uf')
    queyrset = queryset_ascii
    fieldsets = (
        (None, {
            'fields': ('tipo', 'nome', 'cnpj', 'num_parlamentares')
        }),
        ('Endereço', {
            'fields': ('data_instalacao', 'logradouro', 'bairro',
                       'municipio', 'cep', 'pagina_web','email', 'ult_alt_endereco'),
        }),
        ('Outras informações', {
            'classes': ('collapse',),
            'fields': ('observacoes', 'foto'),
        }),
    )
    raw_id_fields = ('municipio',)
    readonly_fields = ['num_parlamentares',]
    search_fields = ('search_text','cnpj', 'bairro', 'logradouro',
                     'cep', 'municipio__nome', 'municipio__uf__nome',
                     'municipio__codigo_ibge', 'pagina_web', 'observacoes')

    def get_convenios(self, obj):
        return '<ul>' + ''.join(['<li>%s</li>' % c.__unicode__() for c in obj.convenio_set.all()]) + '</ul>'
    get_convenios.short_description = u'Convênios'
    get_convenios.allow_tags= True
    
    def changelist_view(self, request, extra_context=None):
        return super(CasaLegislativaAdmin, self).changelist_view(
            request,
            extra_context={'query_str': '?' + request.META['QUERY_STRING']}
        )
        
    def lookup_allowed(self, lookup, value):
        return super(CasaLegislativaAdmin, self).lookup_allowed(lookup, value) or \
            lookup in ['municipio__uf__codigo_ibge__exact', 'convenio__projeto__id__exact']
 

    def etiqueta(self,request,queryset):        
        return labels_report(request,queryset=queryset)
    etiqueta.short_description = "Gerar etiqueta(s) da(s) casa(s) selecionada(s)"

    def etiqueta_sem_presidente(self,request,queryset):        
        return labels_report_sem_presidente(request,queryset=queryset)
    etiqueta_sem_presidente.short_description = "Gerar etiqueta(s) sem presidente da(s) casa(s) selecionada(s)"

    def relatorio(self,request,queryset):        
        return report(request,queryset=queryset)
    relatorio.short_description = u"Exportar a(s) casa(s) selecionada(s) para PDF"

    def relatorio_completo(self,request,queryset):        
        return report_complete(request,queryset=queryset)
    relatorio_completo.short_description = u"Gerar relatório completo da(s) casa(s) selecionada(s)"

    def relatorio_csv(self,request,queryset):        
        return export_csv(request)        
    relatorio_csv.short_description = u"Exportar casa(s) selecionada(s) para CSV"
    
    def adicionar_casas(self, request, queryset):
        if 'carrinho_casas' in request.session:
        #if request.session.has_key('carrinho_casas'):
            q1 = len(request.session['carrinho_casas'])
        else:
            q1 = 0        
        response = adicionar_casas_carrinho(request,queryset=queryset)
        q2 = len(request.session['carrinho_casas'])
        quant = q2 - q1
        if quant:
            self.message_user(request,str(q2-q1)+" Casas Legislativas adicionadas no carrinho" )
        else:
            self.message_user(request,"As Casas Legislativas selecionadas já foram adicionadas anteriormente" )
        return HttpResponseRedirect('.')
    
    adicionar_casas.short_description = u"Armazenar casas no carrinho para exportar"
        
    
    def get_actions(self, request):
        actions = super(CasaLegislativaAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

admin.site.register(CasaLegislativa, CasaLegislativaAdmin)
admin.site.register(TipoCasaLegislativa)
