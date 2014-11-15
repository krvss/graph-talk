"""
.. module:: gt.export
   :platform: Unix, Windows
   :synopsis: Graph-talk export classes, experimental serialization module

.. moduleauthor:: Stas Kravets (krvss) <stas.kravets@gmail.com>

"""

import re

from gt.core import *
from gt.utils import *


def get_printable(obj, double_escape=False):
    """
    Get printable representation of object
    :param obj:             object to print.
    :param double_escape:   use double escape for \n etc or not.
    :return:                printable string
    :rtype:                 str.
    """
    if is_regex(object):
        return '%s' % obj.pattern
    else:
        s = replace_special_chars(str(obj))
        s = ''.join(escape(c) for c in s)

        if double_escape:
            s = s.replace('\\', '\\\\').replace('\\\\"', r'\"')

        return s


class ExportProcess(VisitorProcess):
    """
    Export process is a base class for the serialization processes. It is a child of :class:`gt.core.VisitorProcess`
    with support of writing serialization data to the file while visiting :class:`gt.core.Graph` elements.
    For the better readability, each graph element gets an unique name depending on its class.
    Uses :attr:`gt.core.VisitorProcess.visit_event` event as a trigger for the serialization functions.
    """
    #: Target file name parameter, a part of the start context.
    FILENAME = 'file'

    GRAPH_ID = 'graph'
    TYPE_REGEX = re.compile(ur'([A-Z])*')

    #: Element id pattern.
    ID_PATTERN = '%s_%s'

    def __init__(self):
        super(ExportProcess, self).__init__()

        self._filename = ''
        self._file = None
        self._info = {}

    def start_file(self, new=True):
        """
        Starts the writing to the file.

        :param new: if True, the file content will be cleared.
        :type new:  bool.
        """
        if self._filename:
            self._file = open(self._filename, mode='w' if new else 'w+')

    def write_file(self, data):
        """
        Write data to the open file.

        :param data: data to be written, the carriage return will be added automatically.
        :type data:  str.
        """
        self._file.write(str(data) + '\n')

    def stop_file(self, finished=True):
        """
        Stops the writing to the file and closes it.

        :param finished:    True if the process is finished.
        :type finished:     bool.
        """
        if self._file:
            self._file.close()
            self._file = None

    def get_type_id(self, element):
        """
        Converts the element type to the id, for example :class:`gt.core.ComplexNotion` will be converted to "cn",
        :class:`gt.core.Relation` will be converted to "r" and so on.

        :param element: object to get the type id.
        :rtype:         str.
        :return:        class name converted to id.
        """
        if isinstance(element, Graph):
            type_id = self.GRAPH_ID
        else:
            type_id = ''.join(re.findall(self.TYPE_REGEX, element.__class__.__name__)).lower()

        return type_id

    def get_serial_id(self, type_id):
        """
        Gets the serialization id for the specified type: "type_id_NN", where NN is a 0-based counter for the type.
        Increases the counter after use. Uses :attr:`ExportProcess.ID_PATTERN` as a template.

        :param type_id: type identifier
        :type type_id:  str.
        :rtype:         str.
        :return:        serialization id for the type.
        """
        counter = self._info.get(type_id, 0)
        self._info[type_id] = counter + 1

        return self.ID_PATTERN % (type_id, counter)

    def get_object_id(self, obj):
        """
        Gets the non-graph element identifier.

        :param obj: input object.
        :return:    object id.
        :rtype:     str.
        """
        return get_object_name(obj)

    def get_element_id(self, element):
        """
        Gets the unique element serialization id. Safe to call multiple times, will return the same id for the same
        element.

        :param element: serializing object.
        :rtype:         str.
        :return:        element id string.
        """
        element_id = self._info.get(element)

        if element_id:
            return element_id

        element_id = self.get_serial_id(self.get_type_id(element)) if isinstance(element, Element) else \
            self.get_object_id(element)

        self._info[element] = element_id

        return element_id

    def export_graph(self, graph):
        """
        Called when graph is visited for serialization.

        :param graph:   serializing graph.
        :rtype:         str.
        :return:        export string to write to the file or None.
        """
        pass

    def export_notion(self, notion):
        """
        Called when notion is visited for serialization.

        :param notion:  serializing notion.
        :rtype:         str.
        :return:        export string to write to the file or None.
        """
        pass

    def export_relation(self, relation):
        """
        Called when relation is visited for serialization.

        :param relation:    serializing graph.
        :rtype:             str.
        :return:            export string to write to the file or None.
        """
        pass

    def on_export(self):
        """
        Export event, calls :meth:`ExportProcess.export_graph`, :meth:`ExportProcess.export_notion`, or
        :meth:`ExportProcess.export_relation` depending on :attr:`gt.core.Process.current` element type.
        If export data is not empty it will be written to the file using :meth:`ExportProcess.write_file`.

        :return:    True
        :rtype:     bool.
        """
        export_data = ''

        if isinstance(self.current, Notion):
            export_data = self.export_notion(self.current)
        elif isinstance(self.current, Relation):
            export_data = self.export_relation(self.current)
        elif isinstance(self.current, Graph):
            export_data = self.export_graph(self.current)

        if export_data:
            self.write_file(export_data)

        return True

    def on_new(self, message, context):
        """
        Gets the file name from :attr:`ExportProcess.FILENAME` context parameter, opens it using
        :meth:`ExportProcess.start_file` with new=True and clears internal counters.
        """
        super(ExportProcess, self).on_new(message, context)

        self._filename = self.context.pop(self.FILENAME)
        self._info.clear()
        self.start_file()

    def on_resume(self, message, context):
        """
        Opens current :attr:`ExportProcess.filename` to continue the writing using :meth:`ExportProcess.start_file`
        with new=False.
        """
        super(ExportProcess, self).on_resume(message, context)

        self.start_file(False)

    def handle(self, message, context):
        """
        In addtion to :meth:`gt.core.Process.handle` closes the file, calling :meth:`ExportProcess.stop_file`.
        """
        result = super(ExportProcess, self).handle(message, context)
        self.stop_file(result[0] in (self.OK, True, None))

        return result

    def setup_events(self):
        """
        In addition to :meth:`gt.core.Process.setup_events` adds :meth:`ExportProcess.on_export` as a visit event.
        """
        super(ExportProcess, self).setup_events()

        self.visit_event = Event(self.on_export)

    @property
    def filename(self):
        """
        Target file name (read-only).

        :return: current file name.
        :rtype: str.
        """
        return self._filename


class DotExport(ExportProcess):
    EMPTY = 'empty'
    OBJECTS_ID = 'objects'

    MAX_RELATION_LABEL = 80
    MAX_NOTION_LABEL = 20

    def get_condition_string(self, relation):
        if isinstance(relation, NextRelation) and relation.condition_access != TRUE_CONDITION:

            if relation.condition_access.mode in Access.CACHEABLE:
                return get_object_name(relation.condition_access._value)
            elif relation.condition_access.spec == Condition.REGEX:
                return str(relation.condition_access._value.pattern)
            else:
                return str(relation.condition_access._value)

        return ''

    def get_export_string(self, node_string, **attributes):
        label_string = attributes.get('label', '')
        max_len = attributes.get('max_len')

        if max_len and len(label_string) > max_len:
            fit_label = ''
            c = 0

            for l in label_string.split(' '):
                if (c + len(l)) > max_len:
                    fit_label += '\n'
                    c = 0

                c += len(l) + 1
                fit_label += l + ' '

            attributes['label'] = fit_label

        attr_str = '[%s]' % ', '.join(['%s = %s' % (k, v) for k, v in attributes.iteritems()]) if attributes else ''

        return node_string + attr_str

    def get_object_id(self, obj):
        obj_id = super(DotExport, self).get_object_id(obj)

        objects = self._info.get(self.OBJECTS_ID, [])
        objects.append(obj_id)

        self._info[self.OBJECTS_ID] = objects

        return obj_id

    def get_element_id(self, element):
        if not element:
            return self.get_serial_id(self.EMPTY)

        return super(DotExport, self).get_element_id(element)

    def export_graph(self, graph):
        return 'digraph %s {' % self.get_element_id(graph)

    def export_notion(self, notion):
        return self.get_export_string(self.get_element_id(notion),
                                      label='"%s"' % get_printable(notion.name, True),
                                      shape='doublecircle' if isinstance(notion, SelectiveNotion) else 'circle',
                                      color='red' if isinstance(notion, ActionNotion) else 'black',
                                      max_len=self.MAX_NOTION_LABEL)

    def export_relation(self, relation):
        return self.get_export_string('%s -> %s' % (self.get_element_id(relation.subject),
                                                    self.get_element_id(relation.object)),
                                      label='"%s"' % get_printable(self.get_condition_string(relation), True),
                                      color='red' if isinstance(relation, ActionRelation) else 'black',
                                      style='"bold"' if (isinstance(relation.subject, SelectiveNotion) and
                                                       relation.subject.default == relation) else '""',
                                      max_len=self.MAX_RELATION_LABEL,
                                      fontcolor='blue')

    def export_empty(self, counter):
        return self.get_export_string(self.ID_PATTERN % (self.EMPTY, counter),
                                      shape='"point"')

    def export_object(self, name):
        return self.get_export_string(name,
                                      color='red',
                                      shape='"rect"')

    def stop_file(self, finished=True):
        if finished:
            if self.EMPTY in self._info:
                for i in xrange(0, self._info.get(self.EMPTY)):
                    self.write_file(self.export_empty(i))

            for obj_id in self._info.get(self.OBJECTS_ID, []):
                    self.write_file(self.export_object(obj_id))

            if self.GRAPH_ID in self._info:
                for i in xrange(0, self._info.get(self.GRAPH_ID)):
                    self.write_file('}')

        super(DotExport, self).stop_file(finished)
