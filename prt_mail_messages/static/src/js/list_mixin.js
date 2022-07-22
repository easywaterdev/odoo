/** @odoo-module **/

import fieldUtils from "web.field_utils";

export const MessageListController = {
    _getPagingInfo: function (state) {
        if (!state.count) {
            return null;
        }
        var pager = this._super(...arguments);
        if (state.model === "mail.message" || this.modelName === "mail.message") {
            pager.editable = false;
        }
        return pager;
    },
};

export const MessageListModel = {
    _searchReadUngroupedList: function (list) {
        if (list.model !== "mail.message" || list.res_ids.length === 0) {
            return this._super.apply(this, arguments);
        }
        var self = this;
        var fieldNames = list.getFieldNames();
        var prom;
        if (list.__data) {
            // the data have already been fetched (alonside the groups by the
            // call to 'web_read_group'), so we can bypass the search_read
            prom = Promise.resolve(list.__data);
        } else {
            // Cetmix Changes Start: add values to context. Will use them in backend to render paging properly
            prom = this._rpc({
                route: "/web/dataset/search_read",
                model: list.model,
                fields: fieldNames,
                context: _.extend({}, list.getContext(), {
                    bin_size: true,
                    first_id: list.res_ids[0],
                    last_id: list.res_ids[list.res_ids.length - 1],
                    last_offset: list.last_offset ? list.last_offset : 0,
                    list_count: list.count,
                }),
                domain: list.domain || [],
                limit: list.limit,
                offset: list.loadMoreOffset + list.offset,
                orderBy: list.orderedBy,
            });
            // Cetmix changed end.
        }
        return prom.then(function (result) {
            // Cetmix changes start: Store previous vals
            list.last_offset = list.offset;
            // Cetmin changes end.

            delete list.__data;
            list.count = result.length;
            var ids = _.pluck(result.records, "id");
            var data = _.map(result.records, function (record) {
                var dataPoint = self._makeDataPoint({
                    context: list.context,
                    data: record,
                    fields: list.fields,
                    fieldsInfo: list.fieldsInfo,
                    modelName: list.model,
                    parentID: list.id,
                    viewType: list.viewType,
                });

                // add many2one records
                self._parseServerData(fieldNames, dataPoint, dataPoint.data);
                return dataPoint.id;
            });
            if (list.loadMoreOffset) {
                list.data = list.data.concat(data);
                list.res_ids = list.res_ids.concat(ids);
            } else {
                list.data = data;
                list.res_ids = ids;
            }
            self._updateParentResIDs(list);
            return list;
        });
    },
};

export const MessageListRenderer = {
    _renderBodyCell: function (record, node, colIndex, options) {
        if (
            !(record.model === "mail.message" || record.model === "cetmix.conversation")
        ) {
            return this._super.apply(this, arguments);
        }
        var tdClassName = "o_data_cell oe_read_only";
        var $td = $("<td>", {class: tdClassName, tabindex: -1});

        // We register modifiers on the <td> element so that it gets the correct
        // modifiers classes (for styling)
        var modifiers = this._registerModifiers(
            node,
            record,
            $td,
            _.pick(options, "mode")
        );
        // If the invisible modifiers is true, the <td> element is left empty.
        // Indeed, if the modifiers was to change the whole cell would be
        // rerendered anyway.
        if (modifiers.invisible && !(options && options.renderInvisible)) {
            return $td;
        }

        this._handleAttributes($td, node);
        this._setDecorationClasses($td, this.fieldDecorations[node.attrs.name], record);

        var name = node.attrs.name;
        var field = this.state.fields[name];
        var value = record.data[name];
        var formatter = fieldUtils.format[field.type];
        var formatOptions = {
            escape: true,
            data: record.data,
            isPassword: false,
            digits: false,
        };
        var formattedValue = formatter(value, field, formatOptions);
        return $td.html(formattedValue);
    },
};
