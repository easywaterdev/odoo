/** @odoo-module **/

import {getMessagingComponent} from "@mail/utils/messaging_component";
import {patch} from "web.utils";
import {clear} from "@mail/model/model_field_command";

const components = {
    ChatterContainer: getMessagingComponent("ChatterContainer"),
};

Object.assign(components.ChatterContainer.props, {
    previewMessageId: {
        type: Number,
        optional: true,
    },
});

Object.defineProperty(components.ChatterContainer.props, "previewMessageId", {
    value: {
        type: Number,
        optional: true,
    },
    writable: true,
    configurable: true,
    enumerable: true,
});

patch(
    components.ChatterContainer,
    "prt_mail_messages_pro/static/src/components/chatter_container/chatter_container.js",
    {
        async _insertFromProps(props) {
            const values = Object.assign({}, props);
            if (values.threadId === undefined) {
                values.threadId = clear();
            }
            if (!this.chatter) {
                this.chatter = this.env.models["mail.chatter"].create(values);
            } else {
                this.chatter.update(values);
            }
            this.chatter.thread.update({
                displayNotifications: true,
                displayNotes: true,
                displayMessages: true,
            });
        },
    }
);
