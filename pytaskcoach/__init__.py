from pprint import pprint
from xml.etree.ElementTree import parse

XPATHSEP = '/'
XPATH_MATCH_PREFIX = '.{0}{0}'.format(XPATHSEP)

def get_tasks_missing_parent_categories(taskfile_path):
    """Tasks with missing parent categories

    Tasks for which below is true:

    - Task `t` belongs to subcategory `s`
    - Task `t` does not belong to any parent of `s`
    """
    doc = parse(taskfile_path)
    for i in get_subcategories_wo_children(taskfile_path):
        parcats = set(get_parent_categories(i, taskfile_path))
        tasks = set(get_categorizables(i, taskfile_path))
        parcats_tsks = set()
        misparcats = set()

        for parcat in parcats:
            parcats_tsks = set(get_categorizables(parcat, taskfile_path))
            misparcats |= tasks - parcats_tsks

        for misparcat in misparcats:
            yield doc.find(".//task[@id='{}']".format(misparcat))

def get_subcategories(taskfile_path):
    doc = parse(taskfile_path)
    parcats = doc.findall('./category')
    for parcat in parcats:
        for subcat in parcat.findall('.//category'):
            yield subcat

def get_subcategories_wo_children(taskfile_path):
    subcats = get_subcategories(taskfile_path)
    for subcat in subcats:
        if not subcat.findall('.//category'):
            yield subcat

def get_parent_categories(subcat, taskfile_path):
    matcher_tmpl = ".//category[@id='{}']/.."
    doc = parse(taskfile_path)
    matcher = matcher_tmpl.format(subcat.get('id'))
    parcat = doc.find(matcher)
    while parcat and parcat.tag != 'tasks':
        yield parcat
        matcher = matcher_tmpl.format(parcat.get('id'))
        parcat = doc.find(matcher)

def get_categorizables(category, taskfile_path):
    matcher_tmpl = ".//task[@id='{}']"
    doc = parse(taskfile_path)
    tskids = category.get('categorizables')
    assert tskids
    for tskid in tskids.split():
        matcher = matcher_tmpl.format(tskid)
        tsk = doc.find(matcher)
        yield tsk.get('id')
