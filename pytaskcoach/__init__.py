import sys
from xml.etree.ElementTree import parse
from os.path import isdir, join
from glob import iglob
from datetime import datetime, timedelta

import matplotlib.pyplot as plt

# syspol reference
file_ext = '.tsk'

DEFAULT_TIMEDELTA = timedelta(weeks=1)
DEFAULT_DATETIME_FMT = '%Y-%m-%d %H:%M:%S'
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

def validate_tskfile(tskfp):
    """Validate single TaskCoach files

    Parameters
    ----------
    tskfp: str
        Path to a TaskCoach file

    Returns
    -------

    ``True`` if TaskCoach file valid, else ``False``
    """
    MSGTMPL = 'Invalid task with subject `{}` in file `{}`'
    invalid = list(get_tasks_missing_parent_categories(tskfp))
    if invalid:
        for i in invalid:
            tsksubject = i.get('subject')
            print(MSGTMPL.format(tsksubject, tskfp), file=sys.stderr)

    return not invalid

def validate(tskpaths):
    """Validate set of TaskCoach files

    Parameters
    ----------

    tskpaths: Iterable of strings
        Each string is a path to a dir with TaskCoach files as direct
        children

    Returns
    -------

    ``True`` if all TaskCoach files valid, else ``False``
    """
    for dirpath in tskpaths:
        for tskfp in iglob(join(dirpath, '*'+file_ext)):
            if not validate_tskfile(tskfp):
                return False
    return True

def get_category_efforts(categories=(), start=None, end=None, *, paths=None):
    if start is None:
        start = datetime.now() - DEFAULT_TIMEDELTA

    efforts = {}
    if paths is not None:
        for path in paths:
            if isdir(path):
                for tsk in iglob(join(path, '*'+file_ext)):
                    for ctg, eff in _tsk_file_get_category_efforts(categories,
                            tsk, start, end):
                        efforts[ctg] = efforts.get(ctg, timedelta()) + eff

    for ctg, eff in efforts.items():
        yield (ctg, eff.total_seconds())

def plot_category_efforts(data, fnames=()):
    if not len(fnames):
        return
    categories = tuple(record[0] for record in data)
    effort = tuple(record[1] for record in data)
    plt.pie(effort, labels=categories, shadow=True)
    plt.axis('equal')
    for fname in fnames:
        plt.savefig(fname)

def _tsk_file_get_category_efforts(categories, tskfp, start, end):
    doc = parse(tskfp)

    for subjsel in categories:
        effort_time = timedelta()
        match = (XPATH_MATCH_PREFIX +
                XPATHSEP.join("category[@subject='{}']".format(i)
                    for i in subjsel.split(XPATHSEP)))
        category = doc.find(match)
        try:
            tasks = category.get('categorizables')
            for taskid in tasks.split():
                effort_time += get_task_effort(taskid, tskfp, start, end)
            yield (subjsel, effort_time)
        except AttributeError:
            continue

def get_task_effort(tskid, tskfp, start, end=None):
    effort_time = timedelta()
    doc = parse(tskfp)
    task = doc.find(".//task[@id='{}']".format(tskid))
    if task is None:
        return effort_time

    for effort in task.iterfind('effort'):
        try:
            effort_start = datetime.strptime(effort.get('start'),
                    DEFAULT_DATETIME_FMT)
            effort_end = datetime.strptime(effort.get('stop'),
                    DEFAULT_DATETIME_FMT)
        except TypeError:
            #print('Effort id `{}` has no stop attribute'.format(
                #effort.get('id')), file=sys.stderr)
            continue
        if effort_start < start:
            continue
        if end is not None and effort_end > end:
            continue
        effort_time += effort_end - effort_start

    return effort_time
