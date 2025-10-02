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

.. jinja:: model_check

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
