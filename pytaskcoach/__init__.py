import sys
from xml.etree.ElementTree import parse
from os.path import isdir, join
from glob import iglob
from datetime import datetime, timedelta

# syspol reference
file_ext = '.tsk'

DEFAULT_TIMEDELTA = timedelta(weeks=1)
DEFAULT_DATETIME_FMT = '%Y-%m-%d %H:%M:%S'
XPATHSEP = '/'
XPATH_MATCH_PREFIX = '.{0}'.format(XPATHSEP)
CATEGORY_ELEMENT_NAME = 'category'
CATEGORY_ELEMENT_SUBJECT_ATTRIBUTE_NAME = 'subject'

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
    categorizable_ids = category.get('categorizables')
    if not categorizable_ids:
        errormsg = 'Category `{}` at taskfile `{}` has no tasks'.format(
                category.get('subject'), taskfile_path)
        raise AssertionError(errormsg)
    for tskid in categorizable_ids.split():
        matcher = matcher_tmpl.format(tskid)

        # find may not match an element because the categorizable id
        # may be of an XML element with name != 'task'
        tsk = doc.find(matcher)
        if not tsk:
            continue

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
    efforts = {}
    for path in paths:
        for tsk in iglob(join(path, '*'+file_ext)):
            for ctg, eff in _tsk_file_get_category_efforts(categories,
                    tsk, start, end):
                efforts[ctg] = efforts.get(ctg, timedelta()) + eff

    return efforts.items()

def get_category_efforts_details(categories=(), start=None, end=None, *,
        paths=None):
    tskefts = []
    for path in paths:
        for tsk in iglob(join(path, '*'+file_ext)):
            for tskeft in _tsk_file_get_category_efforts_details(categories,
                    tsk, start, end):
                tskefts.append(tskeft)

    return tskefts

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

def _tsk_file_get_category_efforts_details(categories, tskfp, start, end):
    tskefts = []
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
                for tskeft in get_task_efforts(taskid, tskfp, start, end):
                    tskeft['category'] = subjsel
                    tskefts.append(tskeft)
        except AttributeError:
            continue

    return tskefts

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

def get_task_efforts(tskid, tskfp, start, end=None):
    tskefts = []
    doc = parse(tskfp)
    task = doc.find(".//task[@id='{}']".format(tskid))
    if task is None:
        return tskefts

    for effort in task.iterfind('effort'):
        tskeft = {'task': tskid}
        try:
            tskeft['start'] = datetime.strptime(effort.get('start'),
                    DEFAULT_DATETIME_FMT)
            tskeft['end'] = datetime.strptime(effort.get('stop'),
                    DEFAULT_DATETIME_FMT)
        except TypeError:
            continue
        if tskeft['start'] < start:
            continue
        if tskeft['end'] is not None and tskeft['end'] > end:
            continue
        tskefts.append(tskeft)

    return tskefts

def get_categories(paths):
    for path in paths:
        for tsk_fp in iglob(join(path, '*'+file_ext)):
            for category in get_categories_tsk_fp(tsk_fp):
                yield category

def get_categories_tsk_fp(tsk_fp,
                matcher=XPATH_MATCH_PREFIX + CATEGORY_ELEMENT_NAME):
    doc = parse(tsk_fp)
    for category in doc.iterfind(matcher):
        yield from get_category_subcategories(category, matcher)

def get_category_subcategories(category, matcher, prefix=''):
    category_subject = (
            prefix + category.get(CATEGORY_ELEMENT_SUBJECT_ATTRIBUTE_NAME))
    yield category_subject
    for subcategory in category.iterfind(matcher):
        yield from get_category_subcategories(
                            subcategory, matcher, category_subject + XPATHSEP)
