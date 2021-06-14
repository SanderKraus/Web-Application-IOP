from .models import Technology, Tool, ReferenceSystem, Halbzeug, FctMembership


def variables_item_col(member):
    '''
    Variable spaltenparameter hauptzeit, losgroesse und standmenge
    vom vergleichsbauteil berechnen in abhängigkeit vom Referenzbauteil
    '''
    vol_ref = member.difference_volume
    vol_item = member.difference_volume_item

    # function_vol_ref_col = vol_ref()
    # vol_ref_col = 'vol_ref_col'
    # funktion_vol_item_col = vol_item(item_id=1)
    # vol_item_col = 'vol_item_col'

    relation = vol_item / vol_ref

    th_ref = member.hauptzeit
    nwz_ref = member.standmenge
    nl_ref = member.losgroesse

    hauptzeit_item = relation * th_ref
    standmenge_item = nwz_ref * (1 / relation)
    losgroesse_item = nl_ref * (1 / relation)

    return hauptzeit_item, standmenge_item, losgroesse_item


def cost_ref():

    cost_overview = {
        "cost_fct_column": {},
        "cost_general": {}
    }

    cost_parameter = cost_overview['cost_fct_column']
    cost_fpf = cost_overview['cost_general']

    system = ReferenceSystem.objects.filter('pk')
    refs = system.fctmembership_set.all()
    hz = system.item.halbzeug_set.first()

    # ref_test = [[30,100,1000], [30,100,1000], [30,100,1000]]

    for ref in refs:
        '''
        Alle Kosten die bestimmt werden können ohne Npf_gesamt der Fertigungsprozessfolge
        '''
        tool = Tool.objects.get(id=ref.reference)
        machine = Technology.get(id=tool.technology)

        cost_parameter[tool.name] = {}

        cost_parameter[tool.name]['mittlere_leistung'] = machine.mittlere_leistung
        cost_parameter[tool.name]['betrachtungszeitraum'] = system.betrachtungszeitraum
        cost_parameter[tool.name]['strompreis'] = machine.strompreis
        cost_parameter[tool.name]['laufzeit_jahr'] = system.laufzeit_jahr

        cost_parameter[tool.name]['tn'] = (
            tool.ruestzeit / ref.losgroesse) + (tool.werkzeugwechselzeit / ref.standmenge) + tool.werkstueckwechselzeit
        cost_parameter[tool.name]['tg'] = ref.hauptzeit + \
            cost_parameter[tool.name]['tn']
        cost_parameter[tool.name]['te'] = cost_parameter[tool.name]['tg'] + \
            tool.verteilzeit + tool.erholungszeit
        cost_parameter[tool.name]['npf'] = (
            system.laufzeit_jahr * system.betrachtungszeitraum) / (cost_parameter[tool.name]['te'] / (60 * 60))

        cost_parameter[tool.name]['betriebsstoffkosten'] = tool.betriebsstoffkosten
        cost_parameter[tool.name]['restfertigungsgemeinkosten'] = machine.restfertigungsgemeinkosten
        cost_parameter[tool.name]['Ka'] = (
            machine.anschaffungswert - machine.verkaufserlös) / machine.abschreibungsdauer
        cost_parameter[tool.name]['Kr'] = machine.quadratmeterpreis * \
            machine.platzbedarf
        cost_parameter[tool.name]['Ki'] = machine.anschaffungswert * \
            machine.instandhaltungsfaktor
        cost_parameter[tool.name]['Kz'] = 0.5 * \
            (machine.anschaffungswert + machine.verkaufserlös) * machine.zinsatz
        cost_parameter[tool.name]['Kw'] = tool.werkzeugpreis / ref.standmenge
        cost_parameter[tool.name]['Kl'] = machine.stundenlohn * (1 + system.lohnnebenkostenanteil) * (
            cost_parameter[tool.name]['te'] / (60 * 60)) * machine.bediehnverhaeltnis * machine.fertigungsmittelanzahl

    cost_fpf['npf_max'] = min([v['npf'] for k, v in cost_parameter.items()])
    # print(min([v['npf'] for k, v in cost_parameter.items()]))

    for name in cost_parameter:

        cost_parameter[name]['npa'] = cost_overview['cost_general']['npf_max'] / \
            cost_parameter[name]['betrachtungszeitraum']
        cost_parameter[name]['Ke'] = cost_parameter[name]['mittlere_leistung'] * (cost_parameter[name]['te'] / (
            60 * 60)) * cost_parameter[name]['npa'] * cost_parameter[name]['strompreis']

        cost_parameter[name]['Kmh'] = (cost_parameter[name]['Ka'] + cost_parameter[name]['Kr'] + cost_parameter[name]
                                       ['Ki'] + cost_parameter[name]['Ke'] + cost_parameter[name]['Kz']) / cost_parameter[name]['laufzeit_jahr']
        cost_parameter[name]['Km'] = cost_parameter[name]['Kmh'] * \
            (cost_parameter[name]['te'] / (60 * 60))

        cost_parameter[name]['Kf'] = cost_parameter[name]['Kl'] + \
            cost_parameter[name]['Km'] + \
            cost_parameter[name]['Kw'] + cost_parameter[name]['Kx']
        cost_parameter[name]['Khb'] = cost_parameter[name]['betriebsstoffkosten'] / \
            cost_overview['cost_general']['npf_max']

    cost_fpf['Kf_fpf'] = sum([v['Kf'] for k, v in cost_parameter.items()])

    cost_fpf['Krm'] = hz.volumen * hz.dichte * hz.kilopreis * pow(10, -3)
    cost_fpf['Kma'] = cost_fpf['Krm'] + \
        sum([v['Khb'] for k, v in cost_parameter.items()])

    cost_fpf['Kh'] = cost_fpf['Kf_fpf'] + cost_fpf['Kma']
    cost_fpf['Kh_npf'] = cost_fpf['Kh'] * cost_fpf['npf_max']

    cost_fpf['Gpf'] = system.produktpreis * \
        cost_fpf['npf_max'] - cost_fpf['Kh_npf']

    return cost_overview


def cost_ref():

    cost_overview = {
        "cost_fct_column": {},
        "cost_general": {}
    }

    cost_parameter = cost_overview['cost_fct_column']
    cost_fpf = cost_overview['cost_general']

    system = ReferenceSystem.objects.filter('pk')
    refs = system.fctmembership_set.all()
    hz = system.item.halbzeug_set.first()

    # ref_test = [[30,100,1000], [30,100,1000], [30,100,1000]]

    for ref in refs:
        '''
        Alle Kosten die bestimmt werden können ohne Npf_gesamt der Fertigungsprozessfolge
        '''
        tool = Tool.objects.get(id=ref.reference)
        machine = Technology.get(id=tool.technology)

        hauptzeit_item, standmenge_item, losgroesse_item = variables_item_col(
            ref)

        cost_parameter[tool.name] = {}

        cost_parameter[tool.name]['mittlere_leistung'] = machine.mittlere_leistung
        cost_parameter[tool.name]['betrachtungszeitraum'] = system.betrachtungszeitraum
        cost_parameter[tool.name]['strompreis'] = machine.strompreis
        cost_parameter[tool.name]['laufzeit_jahr'] = system.laufzeit_jahr

        cost_parameter[tool.name]['tn'] = (
            tool.ruestzeit / losgroesse_item) + (tool.werkzeugwechselzeit / standmenge_item) + tool.werkstueckwechselzeit
        cost_parameter[tool.name]['tg'] = hauptzeit_item + \
            cost_parameter[tool.name]['tn']
        cost_parameter[tool.name]['te'] = cost_parameter[tool.name]['tg'] + \
            tool.verteilzeit + tool.erholungszeit
        cost_parameter[tool.name]['npf'] = (
            system.laufzeit_jahr * system.betrachtungszeitraum) / (cost_parameter[tool.name]['te'] / (60 * 60))

        cost_parameter[tool.name]['betriebsstoffkosten'] = tool.betriebsstoffkosten
        cost_parameter[tool.name]['restfertigungsgemeinkosten'] = machine.restfertigungsgemeinkosten
        cost_parameter[tool.name]['Ka'] = (
            machine.anschaffungswert - machine.verkaufserlös) / machine.abschreibungsdauer
        cost_parameter[tool.name]['Kr'] = machine.quadratmeterpreis * \
            machine.platzbedarf
        cost_parameter[tool.name]['Ki'] = machine.anschaffungswert * \
            machine.instandhaltungsfaktor
        cost_parameter[tool.name]['Kz'] = 0.5 * \
            (machine.anschaffungswert + machine.verkaufserlös) * machine.zinsatz
        cost_parameter[tool.name]['Kw'] = tool.werkzeugpreis / standmenge_item
        cost_parameter[tool.name]['Kl'] = machine.stundenlohn * (1 + system.lohnnebenkostenanteil) * (
            cost_parameter[tool.name]['te'] / (60 * 60)) * machine.bediehnverhaeltnis * machine.fertigungsmittelanzahl

    cost_fpf['npf_max'] = min([v['npf'] for k, v in cost_parameter.items()])
    # print(min([v['npf'] for k, v in cost_parameter.items()]))

    for name in cost_parameter:

        cost_parameter[name]['npa'] = cost_overview['cost_general']['npf_max'] / \
            cost_parameter[name]['betrachtungszeitraum']
        cost_parameter[name]['Ke'] = cost_parameter[name]['mittlere_leistung'] * (cost_parameter[name]['te'] / (
            60 * 60)) * cost_parameter[name]['npa'] * cost_parameter[name]['strompreis']

        cost_parameter[name]['Kmh'] = (cost_parameter[name]['Ka'] + cost_parameter[name]['Kr'] + cost_parameter[name]
                                       ['Ki'] + cost_parameter[name]['Ke'] + cost_parameter[name]['Kz']) / cost_parameter[name]['laufzeit_jahr']
        cost_parameter[name]['Km'] = cost_parameter[name]['Kmh'] * \
            (cost_parameter[name]['te'] / (60 * 60))

        cost_parameter[name]['Kf'] = cost_parameter[name]['Kl'] + \
            cost_parameter[name]['Km'] + \
            cost_parameter[name]['Kw'] + cost_parameter[name]['Kx']
        cost_parameter[name]['Khb'] = cost_parameter[name]['betriebsstoffkosten'] / \
            cost_overview['cost_general']['npf_max']

    cost_fpf['Kf_fpf'] = sum([v['Kf'] for k, v in cost_parameter.items()])

    cost_fpf['Krm'] = hz.volumen * hz.dichte * hz.kilopreis * pow(10, -3)
    cost_fpf['Kma'] = cost_fpf['Krm'] + \
        sum([v['Khb'] for k, v in cost_parameter.items()])

    cost_fpf['Kh'] = cost_fpf['Kf_fpf'] + cost_fpf['Kma']
    cost_fpf['Kh_npf'] = cost_fpf['Kh'] * cost_fpf['npf_max']

    cost_fpf['Gpf'] = system.produktpreis * \
        cost_fpf['npf_max'] - cost_fpf['Kh_npf']

    return cost_overview
