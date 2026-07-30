from collections import defaultdict
import re
from typing import List

from django.db.models import Model, Q
from django.http import HttpRequest, JsonResponse
from django.template import Context, Template
from django.template.loader import render_to_string
from django.views import View

from allianceauth.services.hooks import get_extension_logger


logger = get_extension_logger(__name__)


class nested_param_dict(dict):
    """
    Helper to create infinite depth default dicts for setting from params
    """
    def __setitem__(self, item, value):
        if "." in item:
            head, path = item.split(".", 1)
            try:
                head = int(head)
            except ValueError:
                pass
            obj = self.setdefault(head, nested_param_dict())
            obj[path] = value
        else:
            super().__setitem__(item, value)


def defaultdict_to_dict(d):
    """
    Helper to convert default dict back to dict
    """
    if isinstance(d, defaultdict):
        d = {k: defaultdict_to_dict(v) for k, v in d.items()}
    return d


class DataTablesView(View):

    model: Model = None
    columns: List[tuple] = []

    def get_model_qs(self, request: HttpRequest, *args, **kwargs):
        return self.model.objects

    def filter_qs(self, table_conf: dict):
        # Search
        filter_qs = Q()
        for id, c in table_conf["columns"].items():
            _c = self.columns[int(id)][0]
            if c.get("searchable", False) and len(_c) > 0:
                if c.get("columnControl", False):
                    _sv = str(c["columnControl"]["search"]["value"])
                    """contains, equal, ends, starts, empty"""
                    _logic = str(c["columnControl"]["search"]["logic"])
                    """text, date, num"""
                    _type = str(c["columnControl"]["search"]["type"])
                    if _type == "text":
                        if _logic == "empty":
                            filter_qs &= Q(**{f'{_c}': ""})
                        elif len(_sv) > 0:
                            if _logic == "contains":
                                filter_qs &= Q(**{f'{_c}__icontains': _sv})
                            elif _logic == "starts":
                                filter_qs &= Q(**{f'{_c}__istartswith': _sv})
                            elif _logic == "ends":
                                filter_qs &= Q(**{f'{_c}__iendswith': _sv})
                            elif _logic == "equal":
                                filter_qs &= Q(**{f'{_c}': _sv})
                    elif _type == "num":
                        if _logic == "empty":
                            filter_qs &= Q(**{f'{_c}__isnull': True})
                        elif len(_sv) > 0:
                            try:
                                if _logic == "greater":
                                    filter_qs &= Q(**{f'{_c}__gt': float(_sv)})
                                elif _logic == "less":
                                    filter_qs &= Q(**{f'{_c}__lt': float(_sv)})
                                elif _logic == "greaterOrEqual":
                                    filter_qs &= Q(**{f'{_c}__gte': float(_sv)})
                                elif _logic == "lessOrEqual":
                                    filter_qs &= Q(**{f'{_c}__lte': float(_sv)})
                                elif _logic == "equal":
                                    filter_qs &= Q(**{f'{_c}': float(_sv)})
                            except ValueError:
                                pass
                else:
                    _sv = str(c["search"]["value"])
                    if len(_sv) > 0:
                        if c["search"]["regex"]:
                            filter_qs |= Q(**{f'{_c}__iregex': _sv})
                        else:
                            filter_qs |= Q(**{f'{_c}__icontains': _sv})
                _gsv = str(table_conf["search"]["value"])
                if len(_gsv) > 0:
                    filter_qs |= Q(**{f'{_c}__icontains': _gsv})
        return filter_qs

    def except_qs(self, table_conf: dict):
        # Search
        except_qs = Q()
        for id, c in table_conf["columns"].items():
            _c = self.columns[int(id)][0]
            if c.get("searchable", False) and len(_c) > 0:
                if c.get("columnControl", False):
                    _sv = str(c["columnControl"]["search"]["value"])
                    """notContains, notEqual, notEmpty"""
                    _logic = str(c["columnControl"]["search"]["logic"])
                    """text, date, num"""
                    _type = str(c["columnControl"]["search"]["type"])
                    if _type == "text":
                        if _logic == "notEmpty":
                            except_qs |= Q(**{f'{_c}': ""})
                        elif len(_sv) > 0:
                            if _logic == "notContains":
                                except_qs |= Q(**{f'{_c}__icontains': _sv})
                            elif _logic == "notEqual":
                                except_qs |= Q(**{f'{_c}': _sv})
                    elif _type == "num":
                        if _logic == "notEmpty":
                            except_qs |= Q(**{f'{_c}__isnull': False})
                        elif len(_sv) > 0:
                            if _logic == "notEqual":
                                try:
                                    except_qs |= Q(**{f'{_c}': float(_sv)})
                                except ValueError:
                                    pass
        return except_qs

    def get_table_config(self, get: dict):
        _cols = nested_param_dict()
        for c, v in get.items():
            _keys = [_k for _k in c.replace("]", "").split("[")]
            _v = v
            if v in ["true", "false"]:
                _v = _v == "true"
            else:
                try:
                    _v = int(_v)
                except ValueError:
                    pass # not an integer
            _cols[".".join(_keys)] = _v
        return defaultdict_to_dict(_cols)

    def get_order(self, table_conf: dict):
        order = []
        for oc, od in table_conf.get("order", {}).items():
            _c = table_conf["columns"][od["column"]]
            if _c["orderable"]:
                if od["dir"] == "desc":
                    order.append("-" + self.columns[int(od["column"])][0])
                else:
                    order.append(self.columns[int(od["column"])][0])
        return order

    def render_template(self, request: HttpRequest, template: str, ctx: dict):
        if "{{" in template:
            _template = Template(template)
            return _template.render(Context(ctx))
        else:
            return render_to_string(
                template,
                ctx,
                request
            )

    def get(self, request: HttpRequest, *args, **kwargs):
        table_conf = self.get_table_config(request.GET)
        draw = int(table_conf["draw"])
        start = int(table_conf["start"])
        length = int(table_conf["length"])
        if length <= 0:
            logger.warning(
                "Using no pagination is not recommended for server side rendered datatables"
            )
        limit = start + length


        # Build response rows
        items = []
        qs = self.get_model_qs(
            request,
            *args,
            **kwargs
        ).filter(
            self.filter_qs(table_conf)
        ).exclude(
            self.except_qs(table_conf)
        ).order_by(
            *self.get_order(table_conf)
        )

        # Get the count after filtering
        qs_count = qs.count()

        # build output
        if length > 0:
            qs = qs[start:limit]

        for row in qs:
            ctx = {"row": row}
            row = []
            for t in self.columns:
                row.append(self.render_template(request, t[1], ctx))
            items.append(row)

        # Build our output dict
        datatables_data = {}
        datatables_data['draw'] = draw
        datatables_data['recordsTotal'] = self.get_model_qs(request, *args, **kwargs).all().count()
        datatables_data['recordsFiltered'] = qs_count
        datatables_data['data'] = items

        return JsonResponse(datatables_data)
