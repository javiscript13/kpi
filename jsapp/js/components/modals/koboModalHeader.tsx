import React from 'react';
import type {IconName} from 'jsapp/fonts/k-icons';
import bem, {makeBem} from 'js/bem';
import Button from 'jsapp/js/components/common/button';
import Icon from 'jsapp/js/components/common/icon';

bem.KoboModal__header = makeBem(bem.KoboModal, 'header', 'header');
bem.KoboModal__headerIcon = makeBem(bem.KoboModal, 'header-icon', 'span');

export type KoboModalHeaderIconColors = 'blue' | 'red';

interface KoboModalHeaderProps {
  /** Optional icon displayed on the left of the title. */
  icon?: IconName;
  /** Color of the optional icon. Defaults to "blue". */
  iconColor?: KoboModalHeaderIconColors;
  children: React.ReactNode;
  /** Pass this close request callback to display the "x" close button.  */
  onRequestCloseByX?: () => void;
}

export default function KoboModalHeader(props: KoboModalHeaderProps) {
  return (
    <bem.KoboModal__header m={{'has-icon': Boolean(props.icon)}}>
      <h1>
        {props.icon && (
          <bem.KoboModal__headerIcon m={props.iconColor || 'blue'}>
            <Icon name={props.icon} size='s' />
          </bem.KoboModal__headerIcon>
        )}

        {props.children}
      </h1>

      {props.onRequestCloseByX && (
        <Button
          type='bare'
          color='storm'
          size='s'
          startIcon='close'
          onClick={props.onRequestCloseByX}
        />
      )}
    </bem.KoboModal__header>
  );
}
