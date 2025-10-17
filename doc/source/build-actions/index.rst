Build Actions
=============

Execute Scade One model build actions.

Code generation
---------------

.. jinja:: code-gen

    {{ description }}

    {{ inputs_table }}

    {{ outputs_table }}

    Example
    +++++++

    {% for filename, title in examples %}
    .. dropdown:: {{ title }}
       :animate: fade-in

       .. literalinclude:: examples/{{ filename }}
          :language: yaml

    {% endfor %}


Model check
-----------

.. jinja:: model-check

    {{ description }}

    {{ inputs_table }}

    {{ outputs_table }}

    Example
    +++++++

    {% for filename, title in examples %}
    .. dropdown:: {{ title }}
       :animate: fade-in

       .. literalinclude:: examples/{{ filename }}
          :language: yaml

    {% endfor %}

FMU export
----------

.. jinja:: fmu-export

    {{ description }}

    {{ inputs_table }}

    {{ outputs_table }}

    .. admonition:: Limitations
       :class: warning

       **Imported Type**

       The FMU export is not possible if imported types are used for any of the inputs or outputs
       of the selected operator, or sensors in the scope of the export.

       **Supported Platforms**

       This version only supports gcc compiler on 64 bits Windows platform.

    Example
    +++++++

    {% for filename, title in examples %}
    .. dropdown:: {{ title }}
       :animate: fade-in

       .. literalinclude:: examples/{{ filename }}
          :language: yaml

    {% endfor %}