/** @odoo-module **/

import ListController from "web.ListController";
import ListRenderer from "web.ListRenderer";
import ListModel from "web.ListModel";
import ListView from "web.ListView";
import viewRegistry from "web.view_registry";
import {
    MessageListController,
    MessageListModel,
    MessageListRenderer,
} from "./list_mixin";

const MailMessageUpdateListController = ListController.extend(MessageListController);

const MailMessageUpdateListModel = ListModel.extend(MessageListModel);

const MailMessageUpdateListRenderer = ListRenderer.extend(MessageListRenderer);

export const MailMessageUpdateListView = ListView.extend({
    config: Object.assign({}, ListView.prototype.config, {
        Controller: MailMessageUpdateListController,
        Model: MailMessageUpdateListModel,
        Renderer: MailMessageUpdateListRenderer,
    }),
});

viewRegistry.add("mail_messages_update_list", MailMessageUpdateListView);
